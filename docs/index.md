# Hakai API Python Client

`hakai-api` is a thin wrapper around [requests](https://requests.readthedocs.io/) for calling the
[Hakai API](https://hakaiinstitute.github.io/hakai-api/). Its `Client` is a `requests.Session` that
handles login, caches your credentials between sessions, refreshes tokens, and lets you use paths
relative to the API root.

## Install

Requires Python 3.11 or newer.

=== "pip"

    ```bash
    pip install hakai-api
    ```

=== "uv"

    ```bash
    uv add hakai-api
    ```

## Quickstart

```python
from hakai_api import Client

client = Client()  # (1)!

response = client.get("/eims/views/output/chlorophyll?limit=50")  # (2)!
response.raise_for_status()
print(response.json())
# [{'action': '', 'event_pk': 7064, 'rn': '1', 'date': '2012-05-17', 'work_area': 'CALVERT', ...
```

1. The first time this runs, it prints a login URL and asks you to paste the credentials string
   from that page. The credentials are cached in `~/.hakai-api-auth`, so later runs skip the prompt
   until they expire.
2. Paths that start with `/` are appended to the API root (`https://portal.hakai.org/api`).

`Client` subclasses `requests.Session` (via `requests_oauthlib.OAuth2Session`), so `get`, `post`,
`params=`, `json=`, `timeout=`, and the rest of the requests API work as usual.

## Next steps

- [Authentication](guides/authentication.md): pick a login flow and manage credentials in scripts,
  containers, and CI.
- [Configuration](guides/configuration.md): point the client at another API instance and set a user agent.
- [API Reference](reference.md): every public class and method.
- [Hakai API endpoints](https://hakaiinstitute.github.io/hakai-api/): what data you can request.
