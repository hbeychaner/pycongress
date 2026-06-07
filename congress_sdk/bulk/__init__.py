"""GovInfo bulk data client for BILLSTATUS XML files.

Downloads full bill status XML from the GovInfo bulk data repository
(https://www.govinfo.gov/bulkdata/BILLSTATUS/) — no API key required,
no rate limits, full bill data from the 107th Congress onwards.

Quick start::

    from congress_sdk.bulk import GovInfoBulkClient

    client = GovInfoBulkClient()
    records = client.download_congress(
        congress=118,
        bill_types=["hr", "s"],
        outdir=Path("data/bulk/118"),
        workers=40,
    )
"""

from congress_sdk.bulk.govinfo import BILL_TYPES, GovInfoBulkClient
from congress_sdk.bulk.billstatus import parse_billstatus_xml

__all__ = ["GovInfoBulkClient", "BILL_TYPES", "parse_billstatus_xml"]
