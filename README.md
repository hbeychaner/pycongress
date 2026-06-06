# pycongress

Python SDK for the [Congress.gov API](https://api.congress.gov/).  
Covers all 20 resource endpoints with typed Pydantic v2 models, automatic
pagination, exponential-backoff retry, and a spec-driven client that resolves
path and query parameters from response records.

---

## Table of contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Quick start](#quick-start)
- [Client API](#client-api)
- [Endpoint specs](#endpoint-specs)
- [Pydantic models](#pydantic-models)
- [Supported resources](#supported-resources)
- [Advanced usage](#advanced-usage)
- [Package layout](#package-layout)
- [Development](#development)

---

## Installation

```bash
pip install pycongress
# or via uv:
uv add pycongress
```

Install from source (editable):

```bash
git clone https://github.com/hbeychaner/pycongress.git
cd pycongress
uv sync
```

Pin to a specific commit in another project:

```bash
uv add "pycongress @ git+https://github.com/hbeychaner/pycongress.git@<sha>"
```

---

## Configuration

Set `CONGRESS_API_KEY` in your shell environment or a `.env` file at the
project root:

```
CONGRESS_API_KEY=your_key_here
```

Additional optional variables:

| Variable | Default | Purpose |
|---|---|---|
| `CONGRESS_API_URL` | `https://api.congress.gov/v3` | Override base URL |
| `CONGRESS_STRICT_FIELD_CHECK` | `false` | Raise on unrecognised API fields |
| `TIMEOUT_SECS` | `30` | HTTP timeout per request |
| `OPENAI_API_KEY` | — | Required only for AI-powered services |

---

## Quick start

```python
from congress_sdk.data_collection.client import get_client
from congress_sdk.data_collection.endpoint_registry import get_spec

client = get_client()                    # reads CONGRESS_API_KEY from env

# ── Paginate a list endpoint ──────────────────────────────────────────────
spec = get_spec("bill_list")
for page in client.paginate(spec, params={"fromDateTime": "2025-01-01T00:00:00Z",
                                           "toDateTime":   "2025-01-31T23:59:59Z"}):
    for bill in page:
        print(bill.title, bill.congress)

# ── Fetch a single item ───────────────────────────────────────────────────
item_spec = get_spec("bill_item")
bill = client.fetch_one(item_spec, {"congress": 119, "bill_type": "hr", "number": 1})
print(bill.model_dump(mode="json"))

# ── Iterate all pages automatically ──────────────────────────────────────
for record in client.iterate_all(spec, params={"congress": 119}):
    process(record)
```

---

## Client API

`CDGClient` (obtained via `get_client()`) exposes:

| Method | Description |
|---|---|
| `get_client(api_key=None)` | Factory; falls back to `CONGRESS_API_KEY` env var |
| `paginate(spec, params)` | Generator over pages; each page is a list of model instances |
| `fetch_one(spec, params)` | Fetch a single item and return a model instance |
| `iterate_all(spec, params)` | Flatten all pages into a single record iterator |
| `resolve_runtime_params_from_record(spec, record)` | Extract path/query params from a list record |
| `coerce_records(model_cls, records, spec)` | Validate raw dicts into model instances |
| `_request_with_backoff(url, params)` | Raw HTTP GET with exponential-backoff retry |
| `request_for_spec(spec, params)` | Return raw JSON dict for a spec |

All responses are validated against Pydantic v2 models.  
Unknown fields emit a `WARNING` log (and raise if `CONGRESS_STRICT_FIELD_CHECK=true`).

---

## Endpoint specs

Each resource is described by one or more `EndpointSpec` objects registered in the
global registry.  Import the `specs` sub-package to trigger registration:

```python
import congress_sdk.data_collection.specs   # registers all 61 specs
from congress_sdk.data_collection.endpoint_registry import get_spec

spec = get_spec("bill_list")
print(spec.name, spec.endpoint)
```

### All registered specs (61)

| Resource | List spec | Item spec | Extra specs |
|---|---|---|---|
| amendment | `amendment_list` | `amendment_item` | |
| bill | `bill_list` | `bill_item` | `bill_list_all`, `bill_list_by_congress`, `bill_list_by_type`, `bill_actions`, `bill_amendments`, `bill_committees`, `bill_cosponsors`, `bill_details`, `bill_relatedbills`, `bill_subjects`, `bill_summaries`, `bill_summaries_all`, `bill_summaries_by_congress`, `bill_summaries_by_type`, `bill_text`, `bill_titles` |
| bound_congressional_record | `bound_congressional_record_list` | `bound_congressional_record_item` | |
| committee | `committee_list` | `committee_item` | `committee_bills`, `committee_meetings`, `committee_nominations`, `committee_prints`, `committee_reports` |
| committee_meeting | `committee_meeting_list` | `committee_meeting_item` | |
| committee_print | `committee_print_list` | `committee_print_item` | |
| committee_report | `committee_report_list` | `committee_report_item` | |
| congress | `congress_list` | `congress_item` | |
| crsreport | `crsreport_list` | `crsreport_item` | |
| daily_congressional_record | `daily_congressional_record_list` | `daily_congressional_record_item` | |
| hearing | `hearing_list` | `hearing_item` | |
| house_communication | `house_communication_list` | `house_communication_item` | |
| house_requirement | `house_requirement_list` | `house_requirement_item` | |
| house_vote | `house_vote_list` | `house_vote_item` | |
| law | `law_list` | `law_item` | |
| member | `member_list` | `member_item` | |
| nomination | `nomination_list` | `nomination_item` | |
| senate_communication | `senate_communication_list` | `senate_communication_item` | |
| summaries | `summaries_list` | `summaries_item` | |
| treaty | `treaty_list` | `treaty_item` | |

---

## Pydantic models

Models live under `congress_sdk/models/`.  All inherit from `pydantic.BaseModel`
(v2).  List-level models also inherit from `EntityBase` and `RecordTypeBase`.

| File | Key models |
|---|---|
| `bills.py` | `BillListItem`, `BillItem`, `BillAction`, `BillSummary`, … |
| `people.py` | `MemberListItem`, `MemberItem`, `Congress`, `CongressMetadata`, `Session` |
| `other_models.py` | `AmendmentListItem`, `CommitteeListItem`, `CommitteeRef`, `BoundCongressionalRecordListItem`, `NominationListItem`, `TreatyListItem`, … |
| `committees.py` | `CommitteeItem`, `CommitteeReportItem` |
| `nominations.py` | `NominationItem` |
| `communications.py` | `HouseCommunicationItem`, `SenateCommunicationItem` |
| `legislation.py` | `HearingItem`, `HouseVoteItem` |
| `reports.py` | `CommitteeReportItem` |
| `shared.py` | `EntityBase`, `Format`, `CountUrl` |
| `meta_models.py` | Pagination, response envelope models |

---

## Supported resources

All 20 Congress.gov API resource types are supported:

| Resource | Date filter | Requires congress | Notes |
|---|---|---|---|
| amendment | ✓ `fromDateTime` / `toDateTime` | — | |
| bill | ✓ | — | |
| bound_congressional_record | — | — | Static; 93 k+ records |
| committee | ✓ | — | `parent` / `subcommittees` nested |
| committee_meeting | ✓ | — | |
| committee_print | ✓ | — | |
| committee_report | ✓ | — | |
| congress | — | — | Returns all 119 congresses |
| crsreport | ✓ | — | |
| daily_congressional_record | ✓ | — | |
| hearing | — | optional | |
| house_communication | ✓ | — | |
| house_requirement | — | — | |
| house_vote | — | ✓ | |
| law | — | ✓ | Item endpoint unreliable; use bill fallback |
| member | ✓ | — | |
| nomination | ✓ | — | |
| senate_communication | ✓ | — | |
| summaries | ✓ | — | List-only (no item endpoint) |
| treaty | ✓ | — | |

---

## Advanced usage

### Date-windowed ingest

```python
spec = get_spec("amendment_list")
records = list(client.iterate_all(spec, params={
    "fromDateTime": "2025-01-01T00:00:00Z",
    "toDateTime":   "2025-01-31T23:59:59Z",
}))
```

### Resolve item params from a list record

```python
list_spec = get_spec("amendment_list")
item_spec = get_spec("amendment_item")

for page in client.paginate(list_spec):
    for record in page:
        params = client.resolve_runtime_params_from_record(item_spec, record.model_dump(mode="json"))
        item   = client.fetch_one(item_spec, params)
```

### Congress-scoped resources

```python
spec = get_spec("house_vote_list")
votes = list(client.iterate_all(spec, params={"congress": 119}))
```

### Raw JSON (no model coercion)

```python
raw = client.request_for_spec(get_spec("bill_item"),
                               {"congress": 119, "bill_type": "hr", "number": 1})
print(raw)   # plain dict
```

---

## Package layout

```
congress_sdk/
├── config.py                   ← env-var config (CONGRESS_API_KEY, etc.)
├── data_collection/
│   ├── client.py               ← CDGClient: HTTP, retry, pagination
│   ├── endpoint_registry.py    ← global spec registry (get_spec / register_spec)
│   ├── endpoint_spec.py        ← EndpointSpec dataclass
│   ├── id_utils.py             ← canonical_id / parse_url_to_id helpers
│   ├── utils.py                ← resolve_pagination and misc helpers
│   └── specs/                  ← 20 spec files (one per resource)
│       ├── amendment_specs.py
│       ├── bill_specs.py
│       └── … (18 more)
├── models/
│   ├── shared.py               ← EntityBase, Format, CountUrl
│   ├── bills.py                ← Bill models (~1 100 lines)
│   ├── people.py               ← Member / Congress models
│   ├── other_models.py         ← All remaining list-item models
│   ├── committees.py           ← Committee detail models
│   ├── communications.py       ← House/Senate communication models
│   ├── legislation.py          ← Hearing, HouseVote models
│   ├── nominations.py          ← Nomination models
│   ├── reports.py              ← Committee report models
│   └── meta_models.py          ← Pagination / envelope models
├── services/                   ← Optional OpenAI / Selenium helpers
├── streamlit/                  ← Optional Streamlit UI components
└── utils/
    └── logger.py               ← Structured logging helper
```

---

## Development

```bash
# Install all extras (includes bs4, openai, etc.)
uv sync --all-extras

# Run tests
uv run pytest tests/ -q

# Run a quick live smoke-test (requires CONGRESS_API_KEY)
uv run python -c "
from congress_sdk.data_collection.client import get_client
import congress_sdk.data_collection.specs
from congress_sdk.data_collection.endpoint_registry import get_spec
client = get_client()
page = next(client.paginate(get_spec('congress_list')))
print(f'Fetched {len(page)} congress records')
"
```

### Updating a spec or model

1. Edit the relevant file in `congress_sdk/data_collection/specs/` or `congress_sdk/models/`.
2. Add or update the corresponding test in `tests/`.
3. Run `uv run pytest tests/ -q` to verify.
4. Commit, push, then update the pinned SHA in any downstream projects:
   ```bash
   uv lock --upgrade-package pycongress && uv sync
   ```
