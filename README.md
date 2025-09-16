# Hakai Api Python Client

This project exports a single Python class that can be used to make HTTP requests to the
Hakai API resource server.
The exported `Client` class extends the functionality of the
Python [requests library](https://docs.python-requests.org/en/master/) to supply Hakai
OAuth2 credentials with url requests.

![PyPI](https://img.shields.io/pypi/v/hakai-api)   [![tests](https://github.com/HakaiInstitute/hakai-api-client-py/actions/workflows/test.yaml/badge.svg)](https://github.com/HakaiInstitute/hakai-api-client-py/actions/workflows/test.yaml)  [![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](https://opensource.org/licenses/MIT)

<details>

<summary>Table of Contents</summary>

[Installation](#installation)

[Quickstart](#quickstart)
- [Desktop OAuth Flow](#desktop-oauth-flow)
- [User Agent Configuration](#user-agent-configuration)

[Methods](#methods)

[API endpoints](#api-endpoints)

[Advanced usage](#advanced-usage)
- [Custom API Endpoints](#custom-api-endpoints)
- [Relative Endpoint Support](#relative-endpoint-support)
- [Credentials Configuration](#credentials-configuration)

[Contributing](#contributing)

</details>

# Installation

Python 3.8 or higher is required. Install with pip:

```bash
pip install hakai-api
```

# Quickstart

```python
from hakai_api import Client

# Get the api request client
client = Client()  # Follow stdout prompts to get an API token

# Make a data request for chlorophyll data (using relative endpoint)
response = client.get('/eims/views/output/chlorophyll?limit=50')

print(response.json())
# [{'action': '', 'event_pk': 7064, 'rn': '1', 'date': '2012-05-17', 'work_area': 'CALVERT'...
```

## Desktop OAuth Flow

For native applications and automated scripts, use the desktop OAuth flow with PKCE:

```python
from hakai_api import Client

# Use desktop OAuth flow (opens browser, more secure)
client = Client(auth_flow="desktop")

# Or use the factory method
client = Client.create_desktop_client()

# Make requests using relative endpoints
response = client.get('/eims/views/output/stations')
print(response.json())
```

## User Agent Configuration

**Important**: Set a descriptive user agent to help identify your application on the backend. Often the repository url is a good way to identify yourself:

```python
from hakai_api import Client
import os

# Set user agent during initialization
client = Client(user_agent="MyApp/1.0 (contact@example.com)")

# Or set via environment variable
os.environ['HAKAI_API_USER_AGENT'] = "MyApp/1.0 (contact@example.com)"
client = Client()

# Methods

This library exports a single client name `Client`. Instantiating this class produces
a `requests.Session` client from the Python requests library. The Hakai API Python
Client inherits directly from `requests.Session` thus all methods available on that
parent class are available. For details see
the [requests documentation](http://docs.python-requests.org/).

The hakai_api `Client` class also contains a property `api_root` which is useful for
constructing urls to access data from the API. The
above [Quickstart example](#quickstart) demonstrates using this property to construct a
url to access project names.

# API endpoints

For details about the API, including available endpoints where data can be requested
from, see the [Hakai API documentation](https://github.com/HakaiInstitute/hakai-api).

# Advanced usage

## Custom API Endpoints

You can specify which API to access when instantiating the Client. By default, the API
uses `https://hecate.hakai.org/api` as the API root. It may be useful to use this
library to access a locally running API instance or to access the Goose API for testing
purposes. If you are always going to be accessing data from a locally running API
instance, you are better off using the requests.py library directly since Authorization
is not required for local requests.

```python
from hakai_api import Client

# Get a client for a locally running API instance
client = Client("http://localhost:8666")
print(client.api_root)  # http://localhost:8666
```

## Relative Endpoint Support

The client supports relative endpoints that automatically prepend the API root:

```python
from hakai_api import Client

client = Client()

# These are equivalent:
response1 = client.get('/eims/views/output/stations')
response2 = client.get('https://hecate.hakai.org/api/eims/views/output/stations')
```

## Credentials Configuration

### Direct Credentials

You can pass in the credentials string retrieved from the hakai API login page
while initiating the Client class.

```python
from hakai_api import Client

# Pass a credentials token as the Client Class is initiated
client = Client(credentials="CREDENTIAL_TOKEN")
```

### Environment Variables

Set credentials using the `HAKAI_API_CREDENTIALS` environment variable. This is useful
for e.g. setting credentials in a docker container. The value of the environment variable
should be the credentials token retrieved from the Hakai API login page.

```bash
export HAKAI_API_CREDENTIALS="your_credential_token_here"
```

### Custom Credentials File Location

By default, credentials are saved to `~/.hakai-api-auth`. You can customize this location:

```python
from hakai_api import Client

# Set custom credentials file path
client = Client(credentials_file="/path/to/my/credentials")

# Or use environment variable
# export HAKAI_API_CREDENTIALS="/path/to/my/credentials"
client = Client()
```

# Contributing

See [CONTRIBUTING](CONTRIBUTING.md)

# License

See [LICENSE](LICENSE.md)
