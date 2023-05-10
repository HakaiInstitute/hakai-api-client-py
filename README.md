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

[Methods](#methods)

[API endpoints](#api-endpoints)

[Advanced usage](#advanced-usage)

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

# Make a data request for chlorophyll data
url = '%s/%s' % (client.api_root, 'eims/views/output/chlorophyll?limit=50')
response = client.get(url)

print(url)  # https://hecate.hakai.org/api/eims/views/output/chlorophyll...
print(response.json())
# [{'action': '', 'event_pk': 7064, 'rn': '1', 'date': '2012-05-17', 'work_area': 'CALVERT'...
```

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

You can also pass in the credentials string retrieved from the hakai API login page
while initiating the Client class.

```python
from hakai_api import Client

# Pass a credentials token as the Client Class is initiated
client = Client(credentials="CREDENTIAL_TOKEN")
```

Finally, you can set credentials for the client class using the `HAKAI_API_CREDENTIALS`
environment variable. This is useful for e.g. setting credentials in a docker container.
The value of the environment variable should be the credentials token retrieved from the
Hakai API login page.

# Contributing

See [CONTRIBUTING](CONTRIBUTING.md)

# License

See [LICENSE](LICENSE.md)
