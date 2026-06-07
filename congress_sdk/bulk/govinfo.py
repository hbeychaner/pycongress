"""GovInfo Bulk Data client for the BILLSTATUS collection.

Downloads BILLSTATUS XML for bills and resolutions from
https://www.govinfo.gov/bulkdata/BILLSTATUS/ — no API key required,
no rate limits, full data from the 107th Congress onwards.

Usage::

    from congress_sdk.bulk.govinfo import GovInfoBulkClient, BILL_TYPES

    client = GovInfoBulkClient()

    # Discover what's available
    congresses = client.list_congresses()          # [107, 108, ..., 119]
    types = client.list_bill_types(118)            # ['hconres', 'hjres', 'hr', ...]

    # Download all HR bills from the 118th Congress
    records = client.download_congress(
        congress=118,
        bill_types=["hr"],
        outdir=Path("data/bulk/118"),
        workers=40,
    )
"""

from __future__ import annotations

import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator

import requests

from congress_sdk.bulk.billstatus import parse_billstatus_xml

logger = logging.getLogger(__name__)

_BASE = "https://www.govinfo.gov/bulkdata/BILLSTATUS"

# Canonical set of bill/resolution types in the BILLSTATUS collection
BILL_TYPES: list[str] = [
    "hr",       # House Bill
    "s",        # Senate Bill
    "hjres",    # House Joint Resolution
    "sjres",    # Senate Joint Resolution
    "hconres",  # House Concurrent Resolution
    "sconres",  # Senate Concurrent Resolution
    "hres",     # House Simple Resolution
    "sres",     # Senate Simple Resolution
]


class GovInfoBulkClient:
    """HTTP client for the GovInfo BILLSTATUS bulk data repository.

    All public methods are synchronous and thread-safe.  The internal
    ``requests.Session`` is shared across threads for connection pooling;
    GovInfo imposes no rate limits on its bulk data endpoints.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = 30,
    ) -> None:
        self._session = session or requests.Session()
        self._session.headers["User-Agent"] = "pycongress-bulk/0.1"
        self._timeout = timeout
        self._session_lock = threading.Lock()  # guard for connection pool state

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_congresses(self) -> list[int]:
        """Return congress numbers available in the BILLSTATUS collection.

        Returns:
            Sorted list of congress numbers, e.g. ``[107, 108, ..., 119]``.
        """
        html = self._get(_BASE + "/")
        nums = re.findall(r"/bulkdata/BILLSTATUS/(\d+)/", html)
        return sorted({int(n) for n in nums})

    def list_bill_types(self, congress: int) -> list[str]:
        """Return bill types available for *congress*.

        Args:
            congress: Congress number (e.g. ``118``).

        Returns:
            Sorted list of bill type strings, e.g. ``['hconres', 'hjres', 'hr', ...]``.
        """
        html = self._get(f"{_BASE}/{congress}/")
        types = re.findall(rf"/bulkdata/BILLSTATUS/{congress}/([a-z]+)/", html)
        return sorted({t for t in types})

    def list_bill_urls(self, congress: int, bill_type: str) -> list[str]:
        """Return the full download URL for every BILLSTATUS XML file of *bill_type*.

        Args:
            congress: Congress number.
            bill_type: Bill type in lowercase (e.g. ``"hr"``).

        Returns:
            List of absolute HTTPS URLs, one per bill, in directory order.
        """
        bill_type = bill_type.lower()
        base = f"{_BASE}/{congress}/{bill_type}"
        html = self._get(base + "/")
        filenames = list(dict.fromkeys(re.findall(r"(BILLSTATUS-\d+\w+\.xml)", html)))
        return [f"{base}/{fn}" for fn in filenames]

    # ------------------------------------------------------------------
    # Streaming download
    # ------------------------------------------------------------------

    def iter_congress(
        self,
        congress: int,
        bill_types: list[str] | None = None,
        *,
        workers: int = 40,
        max_bills: int | None = None,
    ) -> Iterator[dict]:
        """Lazily yield parsed bill dicts, downloading with *workers* threads.

        Args:
            congress: Congress number to download.
            bill_types: Subset of ``BILL_TYPES`` to include. Defaults to all 8.
            workers: Concurrent download threads.
            max_bills: Stop after this many bills (useful for testing).

        Yields:
            Parsed bill dicts (same structure as congress.gov API bill items).
        """
        if bill_types is None:
            bill_types = BILL_TYPES

        all_urls: list[str] = []
        for bt in bill_types:
            logger.info("Listing BILLSTATUS/%d/%s …", congress, bt)
            urls = self.list_bill_urls(congress, bt)
            logger.info("  %d files for %s/%s", len(urls), congress, bt)
            all_urls.extend(urls)

        if max_bills is not None:
            all_urls = all_urls[:max_bills]

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._fetch_bill, url): url for url in all_urls}
            for fut in as_completed(futures):
                result = fut.result()
                if result is not None:
                    yield result

    # ------------------------------------------------------------------
    # Bulk download with persistence
    # ------------------------------------------------------------------

    def download_congress(
        self,
        congress: int,
        bill_types: list[str] | None = None,
        *,
        outdir: Path,
        workers: int = 40,
        max_bills: int | None = None,
        resume: bool = True,
    ) -> list[dict]:
        """Download all BILLSTATUS XML for *congress*, parse, and save to disk.

        Output files written inside *outdir*:

        - ``items.jsonl`` — one JSON record per line (crash-safe, appended
          incrementally during download).
        - ``items.json``  — full list consolidated at the end.

        Args:
            congress: Congress number (e.g. ``118``).
            bill_types: Subset of ``BILL_TYPES`` to download. Defaults to all 8.
            outdir: Directory to write output files (created if absent).
            workers: Concurrent download threads.
            max_bills: Cap total downloads (useful for smoke-testing).
            resume: If ``True``, skip bills already present in ``items.jsonl``.

        Returns:
            List of all parsed bill dicts (pre-existing + newly downloaded).
        """
        if bill_types is None:
            bill_types = BILL_TYPES

        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        # Collect all URLs across requested bill types
        all_urls: list[str] = []
        for bt in bill_types:
            logger.info("Listing BILLSTATUS/%d/%s …", congress, bt)
            urls = self.list_bill_urls(congress, bt)
            logger.info("  %d files for %s/%s", len(urls), congress, bt)
            all_urls.extend(urls)

        if max_bills is not None:
            all_urls = all_urls[:max_bills]

        # Resume: load already-fetched records, collect their ids
        jsonl_path = outdir / "items.jsonl"
        seen_ids: set[str] = set()
        records: list[dict] = []

        if resume and jsonl_path.exists():
            for line in jsonl_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    records.append(rec)
                    if rec.get("id"):
                        seen_ids.add(rec["id"])
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed line in %s", jsonl_path)
            if seen_ids:
                logger.info(
                    "Resume mode: skipping %d already-fetched bills", len(seen_ids)
                )

        # Filter out already-fetched URLs using the URL-derived id
        pending = [u for u in all_urls if self._url_to_id(u) not in seen_ids]
        logger.info(
            "Downloading %d/%d bills (congress=%d, workers=%d)",
            len(pending), len(all_urls), congress, workers,
        )

        if not pending:
            logger.info("Nothing to download.")
        else:
            write_lock = threading.Lock()
            error_count = [0]

            with jsonl_path.open("a", encoding="utf-8") as fh:

                def _fetch_and_write(url: str) -> dict | None:
                    bill = self._fetch_bill(url)
                    if bill is not None:
                        with write_lock:
                            fh.write(
                                json.dumps(bill, ensure_ascii=False, default=str) + "\n"
                            )
                            fh.flush()
                            records.append(bill)
                    else:
                        error_count[0] += 1
                    return bill

                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = [pool.submit(_fetch_and_write, url) for url in pending]
                    done = 0
                    for fut in as_completed(futures):
                        done += 1
                        fut.result()  # re-raise unexpected exceptions
                        if done % 500 == 0 or done == len(pending):
                            logger.info(
                                "  %d/%d done (%d errors)",
                                done, len(pending), error_count[0],
                            )

            logger.info(
                "Downloaded %d bills (%d errors)", len(records) - len(seen_ids),
                error_count[0],
            )

        # Write consolidated items.json
        json_path = outdir / "items.json"
        json_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Saved %d bills to %s", len(records), json_path)
        return records

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch_bill(self, url: str) -> dict | None:
        """Download and parse a single BILLSTATUS XML URL.  Returns None on error."""
        try:
            xml_bytes = self._get(url, raw=True)
            return parse_billstatus_xml(xml_bytes)
        except Exception as exc:
            logger.warning("Failed: %s — %s", url, exc)
            return None

    @staticmethod
    def _url_to_id(url: str) -> str | None:
        """Derive the canonical bill id from a BILLSTATUS XML URL."""
        m = re.search(r"BILLSTATUS-(\d+)([a-z]+)(\d+)\.xml$", url, re.IGNORECASE)
        if m:
            congress, btype, number = m.groups()
            return f"bill:{congress}:{btype.lower()}:{number}"
        return None

    def _get(self, url: str, *, raw: bool = False) -> str | bytes:
        """Issue a GET request, raising for non-2xx status."""
        resp = self._session.get(url, timeout=self._timeout)
        resp.raise_for_status()
        return resp.content if raw else resp.text
