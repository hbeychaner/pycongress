from congress_sdk.data_collection.endpoint_registry import (
    EndpointSpec,
    ParamLocation,
    ParamSpec,
    get_spec,
    register_specs,
)
from congress_sdk.models.other_models import (
    CommitteeMeetingListItem,
    CommitteeMeetingItem,
)


list_spec = EndpointSpec(
    name="committee_meeting_list",
    path_template="/committee-meeting",
    param_specs=[],
    data_key="committeeMeetings",
    response_model=CommitteeMeetingListItem,
)

item_spec = EndpointSpec(
    name="committee_meeting_item",
    path_template="/committee-meeting/{path_tail}",
    param_specs=[
        ParamSpec(
            name="path_tail",
            location=ParamLocation.PATH,
            required=True,
            source_field="_unused",
            extract_from_url_segment="committee-meeting",
        )
    ],
    data_key=None,
    unwrap_key="committeeMeeting",
    response_model=CommitteeMeetingItem,
)

register_specs(list_spec, item_spec)

COMMITTEE_MEETING_LIST_SPEC = get_spec("committee_meeting_list")
COMMITTEE_MEETING_ITEM_SPEC = get_spec("committee_meeting_item")

__all__ = ["COMMITTEE_MEETING_LIST_SPEC", "COMMITTEE_MEETING_ITEM_SPEC"]
