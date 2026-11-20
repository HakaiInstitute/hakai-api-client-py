# API Reference

This page is generated from the docstrings in the `hakai_api` package. `Client` also has every method of
[`requests.Session`](https://requests.readthedocs.io/en/latest/api/#request-sessions). Those methods
aren't listed here.

## Client

::: hakai_api.Client
    options:
      show_root_heading: true
      members:
        - DEFAULT_API_ROOT
        - DEFAULT_LOGIN_PAGE
        - CREDENTIALS_ENV_VAR
        - CREDENTIALS_FILE_ENV_VAR
        - USER_AGENT_ENV_VAR
        - create_web_client
        - create_desktop_client
        - api_root
        - login_page
        - credentials
        - credentials_file
        - request
        - refresh_token
        - file_credentials_are_valid
        - reset_credentials

## Auth strategies

`Client` gets credentials through an auth strategy chosen by `auth_flow`. You only need these classes
if you're writing a custom strategy or testing the login flows directly.

::: hakai_api.auth.AuthStrategy

::: hakai_api.auth.WebAuthStrategy

::: hakai_api.auth.DesktopAuthStrategy
