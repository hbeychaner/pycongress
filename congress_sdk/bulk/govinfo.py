"""GovInfo Bulk Data client for the BILLSTATUS collection.

Downloads BILLSTATUS XML for bills and resolutions from the GovInfo bulk data
repository ZIP archives — no API key required, no rate limits, full data from
the 93rd Congress onwards.

ZIP URL pattern::

    https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{bill_type}/
        BILLSTATUS-{congress}-{bill_type}.zip

Usage::

    from congress_sdk.bulk.govinfo import GovInfoBulkClient, BILL_TYPES
    from pathlib import Path

    client = GovInfoBulkClient()
    congresses = client.list_congresses()
    records = client.download_congress(
        congress=118,
        bill_types=["hr", "s"],
        outdir=Path("data/bulk/118"),
    )
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Iterator

import requests

from congress_sdk.bulk.billstatus import parse_billstatus_xml

logger = logging.getLogger(__name__)

_BASE = "https://www.govinfo.gov/bulkdata/BILLSTATUS"

BILL_TYPES: list[str] = [
    "hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres",
]


class GovInfoBulkClient:
    """HTTP client for the GovInfo BILLSTATUS bulk data ZIP archives.

    Uses one ZIP per congress+type for efficient bulk download.
    No API key or rate limits required.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = 120,
    ) -> None:
        self._session = session or requests.Session()
        self._session.headers["User-Agent"] = "pycongress-bulk/0.1"
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Discovery (via HEAD probing of known ZIP URLs)
    # ------------------------------------------------------------------

    def list_congresses(self, check_range: range | None = None) -> list[int]:
        """Return congress numbers with available BILLSTATUS ZIP archives.

        Probes by issuing HEAD requests for the HR ZIP of each congress number.

        Args:
            check_range: Congress numbers to probe. Defaults to range(93, 120).

        Returns:
            Sorted list of available congress numbers.
        """
        if check_range is None:
            check_range = range(93, 120)
        available = []
        for congress in check_range:
            try:
                resp = self._session.head(self.zip_url(congress, "hr"), timeout=10)
                if resp.status_code == 200:
                    available.append(congress)
            except requests.RequestException:
                pass
        return available

    def list_bill_types(self, congress: int) -> list[str]:
        """Return bill types with available BILLSTATUS ZIP archives for *congress*.

        Args:
            congress: Congress number to probe.

        Returns:
            Sorted list of available bill type strings (subset of BILL_TYPES).
        """
        available = []
        for bt in BILL_TYPES:
            try:
                resp = self._session.head(self.zip_url(congress, bt), timeout=10)
                if resp.status_code == 200:
                    available.append(bt)
            except requests.RequestException:
                pass
        return sorted(available)

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def zip_url(self, congress: int, bill_type: str) -> str:
        """Return the ZIP archive URL for a given congress and bill type."""
        bill_type = bill_type.lower()
        return f"{_BASE}/{congress}/{bill_type}/BILLSTATUS-{congress}-{bill_type}.zip"

    def individual_xml_url(self, congress: int, bill_type: str, number: int | str) -> str:
        """Return the URL for a single BILLSTATUS XML file."""
        bill_type = bill_type.lower()
        return f"{_BASE}/{congress}/{bill_type}/BILLSTATUS-{congress}{bill_type}{number}.xml"

    # ------------------------------------------------------------------
    # ZIP-based streaming iterator
    # ------------------------------------------------------------------

    def iter_zip(
        self,
        congress: int,
        bill_type: str,
        *,
        max_bills: int | None = None,
    ) -> Iterator[dict]:
        """Download the BILLSTATUS ZIP for one congress+type and yield parsed dicts.

        Downloads the ZIP archive into memory, then iterates over its XML
        members.  ZIP archives are typically 1-35 MB.

        Args:
            congress: Congress number.
            bill_type: Bill type in lowercase (e.g. ``"hr"``).
            max_bills: Stop after this many records (for testing/sampling).

        Yields:
            Parsed bill dicts.

        Raises:
            requests.HTTPError: If the ZIP returns a non-2xx status.
        """
        bill_type = bill_type.lower()
        url = self.zip_url(congress, bill_type)
        logger.info("Downloading %s …", url)

        resp = self._session.get(url, timeout=self._timeout)
        resp.raise_for_status()
        logger.info(
            "  %.1f MB received (%d/%s)", len(resp.content) / 1_048_576, congress, bill_type
        )

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        logger.info("  %d XML files in ZIP", len(xml_names))

        count = 0
        for name in xml_names:
            if max_bills is not None and count >= max_bills:
                break
            try:
                yield parse_billstatus_xml(zf.read(name))
                count += 1
            except Exception as exc:
                logger.warning("Parse error in %s: %s", name, exc)

    # ------------------------------------------------------------------
    # Bulk download with persistence
    # ------------------------------------------------------------------

    def download_congress(
        self,
        congress: int,
        bill_types: list[str] | None = None,
        *,
        outdir: Path,
        max_bills: int | None = None,
        resume: bool = True,
    ) -> list[dict]:
        """Download all BILLSTATUS for *congress*, parse, and save to disk.

        Writes two output files inside *outdir*:

        - ``items.jsonl`` — one JSON record per line (appended incrementally).
        - ``items.json``  — full consolidated list written at completion.

        Args:
            congress: Congress number (e.g. ``118``).
            bill_types: Subset of BILL_TYPES to download. Defaults to all eight.
            outdir: Output directory (created if absent).
            max_bills: Cap for testing/sampling.
            resume: Skip bills whose ``id`` is already in ``items.jsonl``.

        Returns:
            List of all parsed bill dicts (including previously saved ones).
        """
        if bill_types is None:
            bill_types = BILL_TYPES

        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        # Resume: load existing records
        jsonl_path = outdir / "items.jsonl"
        seen_ids: set[str] = set()
        records: list[dict] = []

        if resume and jsonl_path.exists():
            for raw_line in jsonl_path.read_text(encoding="utf-8").splitlines():
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    rec = json.loads(raw_line)
                    records.append(rec)
                    if rec.get("id"):
                        seen_ids.add(rec["id"])
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed JSONL line in %s", jsonl_path)
            if seen_ids:
                logger.info("Resume: skipping %d already-saved bills", len(seen_ids))

        total_new = 0
        errors = 0

        with jsonl_path.open("a", encoding="utf-8") as fh:
            for bill_type in bill_types:
                try:
                    for bill in self.iter_zip(congress, bill_type, max_bills=max_bills):
                        bill_id = bill.get("id")
                        if bill_id and bill_id in seen_ids:
                            continue
                        fh.write(json.dumps(bill, ensure_ascii=False, default=str) + "\n")
                        fh.flush()
                        records.append(bill)
                        if bill_id:
                            seen_ids.add(bill_id)
                        total_new += 1
                        if max_bills is not None and total_new >= max_bills:
                            break

                except requests.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code == 404:
                        logger.warning(
                            "No ZIP for %d/%s (404), skipping", congress, bill_type
                        )
                    else:
                        logger.error(
                            "Download failed for %d/%s: %s", congress, bill_type, exc
                        )
                    errors += 1

                if max_bills is not None and total_new >= max_bills:
                    break

        # Consolidate to items.json
        json_path = outdir / "items.json"
        json_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        pre_existing = len(records) - total_new
        logger.info(
            "Congress %d: %d new bills saved (%d pre-existing, %d total, %d errors) → %s",
            congress, total_new, pre_existing, len(records), errors, json_path,
        )
        return records
