# pycongress

Python SDK for the [Congress.gov API](https://api.congress.gov/).

## Installation

```bash
pip install pycongress
# or via uv:
uv add pycongress
```

During development (editable install):

```bash
uv add --editable /path/to/pycongress
```

## Configuration

Set `CONGRESS_API_KEY` in your environment or a `.env` file:

```
CONGRESS_API_KEY=your_key_here
```

## Quick start

```python
from congress_sdk.data_collection.client import get_client

client = get_client()
for bill in client.iterate_pages("/bill", data_key="bills"):
    print(bill["title"])
```

## Package layout

```
congress_sdk/
  config.py               ← env-var config (CONGRESS_API_KEY, etc.)
  data_collection/
    client.py             ← CDGClient — HTTP, retry, pagination
    specs/                ← EndpointSpec definitions per resource
    endpoint_registry.py  ← global spec registry
  models/                 ← Pydantic v2 models per resource
  utils/
  services/               ← optional OpenAI / Selenium helpers
  streamlit/              ← optional Streamlit components
```
