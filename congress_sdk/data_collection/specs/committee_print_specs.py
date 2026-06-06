from congress_sdk.data_collection.endpoint_registry import (
    EndpointSpec,
    ParamLocation,
    ParamSpec,
    get_spec,
    register_specs,
)
from congress_sdk.models.other_models import CommitteePrintListItem, CommitteePrintItem


list_spec = EndpointSpec(
    name="committee_print_list",
    path_template="/committee-print",
    param_specs=[],
    data_key="committeePrints",
    response_model=CommitteePrintListItem,
)

item_spec = EndpointSpec(
    name="committee_print_item",
    path_template="/committee-print/{path_tail}",
    param_specs=[
        ParamSpec(
            name="path_tail",
            location=ParamLocation.PATH,
            required=True,
            source_field="_unused",
            extract_from_url_segment="committee-print",
        )
    ],
    data_key=None,
    unwrap_key="committeePrint",
    response_model=CommitteePrintItem,
)

register_specs(list_spec, item_spec)

COMMITTEE_PRINT_LIST_SPEC = get_spec("committee_print_list")
COMMITTEE_PRINT_ITEM_SPEC = get_spec("committee_print_item")

__all__ = ["COMMITTEE_PRINT_LIST_SPEC", "COMMITTEE_PRINT_ITEM_SPEC"]
