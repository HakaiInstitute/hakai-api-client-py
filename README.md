# Hakai Api Python Client

This project exports a single Python class that can be used to make HTTP requests to the Hakai API resource server.
The exported `Client` class extends the functionality of the Python [requests library](https://docs.python-requests.org/en/master/) to supply Hakai OAuth2 credentials with url requests.

# Installation

```bash
pip install hakai-api
```

# Quickstart

```python
from hakai_api import Client

# Get the api request client
client = Client() # Follow stdout prompts to get an API token

# Make a data request for chlorophyll data
url = '%s/%s' % (client.api_root, 'eims/views/output/chlorophyll?limit=50')
response = client.get(url)

print(url) # https://hecate.hakai.org/api/eims/views/output/chlorophyll...
print(response.json()) # [{'action': '', 'event_pk': 7064, 'rn': '1', 'date': '2012-05-17', 'work_area': 'CALVERT'...
```

# Methods

This library exports a single client name `Client`. Instantiating this class produces a `requests.Session` client from the Python requests library. The Hakai API Python Client inherits directly from `requests.Session` thus all methods available on that parent class are available. For details see the [requests documentation](http://docs.python-requests.org/).

The hakai_api `Client` class also contains a property `api_root` which is useful for constructing urls to access data from the API. The above [Quickstart example](#quickstart) demonstrates using this property to construct a url to access project names.

# API endpoints

For details about the API, including available endpoints where data can be requested from, see the [Hakai API documentation](https://github.com/HakaiInstitute/hakai-api).

# Advanced usage

You can specify which API to access when instantiating the Client. By default, the API uses `https://hecate.hakai.org/api` as the API root. It may be useful to use this library to access a locally running API instance or to access the Goose API for testing purposes. If you are always going to be accessing data from a locally running API instance, you are better off using the requests.py library directly since Authorization is not required for local requests.

```python
# Get a client for a locally running API instance
client = Client("http://localhost:8666")
print(client.api_root) # http://localhost:8666
```

# Development
The business code for this package is in the file [`hakai_api/Client.py`](hakai_api/Client.py).
The `./setup.py` file is important for giving details about how to install the package when users do `pip install hakai-api`.
You must update the semantic version info in setup.py and then push a tag to the Github origin in order for PyPi to build and release a new version of the package.
