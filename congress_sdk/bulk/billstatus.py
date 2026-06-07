"""Parse GovInfo BILLSTATUS XML files into Python dicts.

The BILLSTATUS XML schema mirrors the congress.gov API JSON structure closely,
using the same camelCase field names, so the parsed output can be used directly
as an item record in the ingest pipeline.

Key function: ``parse_billstatus_xml(xml_bytes)`` → dict
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

# Elements whose content is HTML/plain-text (not further parsed as XML structure).
_FLATTEN_TAGS = frozenset(
    {
        "constitutionalAuthorityStatementText",
        "text",  # in <summaries><summary><cdata><text>
        "pre",
    }
)

# Child tags that always indicate a collection, even when there is only one child.
# For example, <amendments><amendment>…</amendments> should always be a list.
_LIST_CHILD_TAGS = frozenset(
    {
        "item",          # primary collection element in BILLSTATUS
        "amendment",     # in <amendments>
        "summary",       # in <summaries>
        "format",        # alternate spelling in some older docs
        "recordedVote",  # in <recordedVotes>
    }
)


def _elem_to_val(elem: ET.Element) -> Any:
    """Recursively convert an ElementTree element to a Python value.

    Rules (in priority order):
    1. No children → return stripped text string (or None if empty).
    2. Tag is in ``_FLATTEN_TAGS`` → join all nested text and return as string.
    3. Children include any ``_LIST_CHILD_TAGS`` elements → return list of those
       children; metadata siblings (``<count>`` etc.) are discarded.
    4. All children share the same tag AND there are 2+ children → return list.
    5. Mixed child tags (or single child with non-list tag) → return dict.
       Duplicate keys are merged into a list.
    """
    children = list(elem)

    # 1. Leaf node
    if not children:
        return (elem.text or "").strip() or None

    # 2. HTML/text container
    if elem.tag in _FLATTEN_TAGS:
        return "".join(elem.itertext()).strip() or None

    # 3. Has known collection-child elements → return them as a list
    list_children = [c for c in children if c.tag in _LIST_CHILD_TAGS]
    if list_children:
        return [_elem_to_val(c) for c in list_children]

    # 4. All 2+ children share the same tag → list
    tags = {c.tag for c in children}
    if len(tags) == 1 and len(children) > 1:
        return [_elem_to_val(c) for c in children]

    # 5. Mixed children (or single child with unique tag) → dict
    result: dict[str, Any] = {}
    for child in children:
        key = child.tag
        val = _elem_to_val(child)
        if key in result:
            existing = result[key]
            if not isinstance(existing, list):
                result[key] = [existing]
            result[key].append(val)
        else:
            result[key] = val

    return result


def parse_billstatus_xml(xml_bytes: bytes | str) -> dict:
    """Parse a BILLSTATUS XML document and return the bill as a dict.

    The returned dict matches the structure of a congress.gov API bill item.
    Additional synthetic keys:
    - ``id``: canonical identifier ``"bill:{congress}:{type_lower}:{number}"``
    - ``_source``: ``"govinfo_bulk"`` to distinguish from API-sourced records.

    Args:
        xml_bytes: Raw XML bytes or decoded string from a BILLSTATUS-*.xml file.

    Returns:
        dict representing the bill, ready for storage or pydantic validation.

    Raises:
        ValueError: If the XML does not contain a ``<bill>`` element.
        xml.etree.ElementTree.ParseError: If the XML is malformed.
    """
    if isinstance(xml_bytes, bytes):
        xml_str = xml_bytes.decode("utf-8", errors="replace")
    else:
        xml_str = xml_bytes

    root = ET.fromstring(xml_str)

    bill_elem = root.find("bill")
    if bill_elem is None:
        raise ValueError("No <bill> element found in BILLSTATUS XML")

    bill: dict = _elem_to_val(bill_elem)  # type: ignore[assignment]
    if not isinstance(bill, dict):
        raise ValueError(f"Expected dict from <bill> element, got {type(bill)}")

    bill["_source"] = "govinfo_bulk"

    # Compute canonical id consistent with the ingest pipeline
    congress = bill.get("congress", "")
    bill_type = (bill.get("type") or "").lower()
    number = bill.get("number", "")
    if congress and bill_type and number:
        bill["id"] = f"bill:{congress}:{bill_type}:{number}"

    return bill
