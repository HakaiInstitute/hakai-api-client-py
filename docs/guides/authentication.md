# Authentication

Every request to the Hakai API needs an OAuth2 access token. `Client` gets one when you create it, caches
it on disk, and attaches it to every request.

## Choosing a flow

| | Web flow (default) | Desktop flow |
|---|---|---|
| How you log in | Open a URL, copy the credentials string, paste it into the terminal | A browser opens; the client receives the token on a local callback server |
| Needs a browser on the same machine | No | Yes |
| Refresh tokens | No | Yes, so sessions are extended without logging in again |
| Good for | SSH sessions, notebooks on remote servers, quick scripts | Desktop apps and scripts run on your own machine |

=== "Web flow"

    ```python
    from hakai_api import Client

    client = Client()  # same as Client(auth_flow="web") or Client.create_web_client()
    ```

    Running this prints a link to the [login page](https://portal.hakai.org/api-client-login). Log in there,
    copy the credentials string, and paste it at the prompt.

=== "Desktop flow"

    ```python
    from hakai_api import Client

    client = Client(auth_flow="desktop")  # or Client.create_desktop_client()
    ```

    The client opens your browser to log in and waits for the redirect on `http://127.0.0.1:65500/callback`.
    Change the port with `local_port=`, and how long it waits (in seconds) with `callback_timeout=`.
    The client uses the OAuth2 authorization code flow with
    [PKCE](https://oauth.net/2/pkce/).

## Where credentials come from

When you create a `Client`, it looks for credentials in this order and uses the first valid, unexpired
set it finds:

1. **The `credentials` argument.** Either the credentials string from the login page or a dict with
   `access_token`, `token_type`, and `expires_at` keys.
2. **The `HAKAI_API_CREDENTIALS` environment variable**, holding a credentials string.
3. **The credentials file**, `~/.hakai-api-auth` by default.
4. **An interactive login** using the selected flow.

Whichever source it uses, the client then writes the credentials to the credentials file. If none of
these work, `Client()` raises `ValueError`.

### Passing credentials directly

```python
from hakai_api import Client

client = Client(credentials="access_token=...&token_type=Bearer&expires_at=1767225600")
```

Read the string from a secret store or environment variable. Don't commit it.

### Using an environment variable

For containers and CI jobs that can't log in interactively, put the credentials string from the login
page in `HAKAI_API_CREDENTIALS`:

```bash
export HAKAI_API_CREDENTIALS="access_token=...&token_type=Bearer&expires_at=1767225600"
```

### Changing the credentials file location

```python
from hakai_api import Client

client = Client(credentials_file="/path/to/credentials")
```

Or set it with the `HAKAI_API_CREDENTIALS_FILE` environment variable:

```bash
export HAKAI_API_CREDENTIALS_FILE="/path/to/credentials"
```

The `credentials_file=` argument takes precedence over `HAKAI_API_CREDENTIALS_FILE`, which takes precedence
over the default `~/.hakai-api-auth`.

!!! note "Older versions used `HAKAI_API_CREDENTIALS` for the file path"

    Setting `HAKAI_API_CREDENTIALS` to a file path still works, but logs a deprecation warning. Use
    `HAKAI_API_CREDENTIALS_FILE` instead.

The file holds a live access token, so keep it out of version control and shared directories.

## Expiry, refresh, and logging out

- **Automatic re-authentication.** If a request gets a `401 Unauthorized` response, the client tries
  to refresh the token (desktop flow only). If that fails, it deletes the cached credentials, runs the
  login flow again, and retries the request once.
- **Refreshing manually.** `client.refresh_token()` returns `True` if it got a new access token. To
  turn refreshing off, pass `use_refresh=False`.
- **Checking the cache.** `client.file_credentials_are_valid()` reports whether the credentials file
  exists and hasn't expired.
- **Logging out.** `client.reset_credentials()` deletes the credentials file, so the next `Client()`
  asks you to log in again.
