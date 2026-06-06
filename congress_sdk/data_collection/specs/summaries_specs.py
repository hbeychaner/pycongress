"""Specs for the /summaries top-level endpoint.

Summaries is a list-only resource — the API exposes no single-item endpoint
keyed by a summary id. The ``summaries_item`` spec below is a sentinel so
the IngestRunner's spec lookup does not fail; the runner treats SUMMARIES as
a list-only resource and never calls the item spec.
"""

from congress_sdk.data_collection.endpoint_registry import (
    EndpointSpec,
    get_spec,
    register_specs,
)
from congress_sdk.models.other_models import BillSummaryListItem


list_spec = EndpointSpec(
    name="summaries_list",
    path_template="/summaries",
    param_specs=[],
    data_key="summaries",
    response_model=BillSummaryListItem,
)

# Sentinel — identical to list_spec so get_spec("summaries_item") resolves.
# Never invoked at runtime (SUMMARIES is handled as list-only in the runner).
item_spec = EndpointSpec(
    name="summaries_item",
    path_template="/summaries",
    param_specs=[],
    data_key="summaries",
    response_model=BillSummaryListItem,
)

register_specs(list_spec, item_spec)

SUMMARIES_LIST_SPEC = get_spec("summaries_list")
SUMMARIES_ITEM_SPEC = get_spec("summaries_item")

__all__ = ["SUMMARIES_LIST_SPEC", "SUMMARIES_ITEM_SPEC"]
