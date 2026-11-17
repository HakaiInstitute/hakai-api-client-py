# Configuration

## User agent

Set a user agent that identifies your application so the Hakai data team can see who is calling the
API and contact you if something breaks. A repository URL or email address works well.

```python
from hakai_api import Client

client = Client(user_agent="kelp-dashboard/1.2 (https://github.com/HakaiInstitute/kelp-dashboard)")
```

If you don't pass `user_agent=`, the client uses the `HAKAI_API_USER_AGENT` environment variable, and
falls back to `hakai-api-client-py` if that isn't set:

```bash
export HAKAI_API_USER_AGENT="kelp-dashboard/1.2 (data@example.org)"
```

## Relative and absolute URLs

Paths that start with `/` are appended to `client.api_root`. Full URLs are used as they are. These
two requests are the same:

```python
client.get("/eims/views/output/stations")
client.get("https://portal.hakai.org/api/eims/views/output/stations")
```

Use `params=` for query strings instead of formatting them into the URL yourself:

```python
response = client.get(
    "/eims/views/output/chlorophyll",
    params={"limit": 50, "work_area": "CALVERT"},
)
```

For the endpoints and query syntax, see the [Hakai API documentation](https://hakaiinstitute.github.io/hakai-api/).

## Using a different API instance

The client points at the production API (`https://portal.hakai.org/api`) by default. To use a
development or local instance, pass `api_root` (and `login_page` if that instance has its own login
page):

```python
from hakai_api import Client

client = Client(api_root="http://localhost:8666")
print(client.api_root)  # http://localhost:8666
```

Credentials are tied to the API instance that issued them. When you switch instances, give each one
its own `credentials_file` so their cached credentials don't overwrite each other.

## Using it like `requests.Session`

`Client` subclasses `requests.Session`, so the usual session settings work:

```python
from requests.adapters import HTTPAdapter, Retry

client = Client()
client.headers["Accept"] = "application/json"
client.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.5)))
```

## Logging

The client logs with [loguru](https://loguru.readthedocs.io/) and doesn't call `disable()` on its
logger, so its messages go to your loguru handlers. To silence it:

```python
from loguru import logger

logger.disable("hakai_api")
```
