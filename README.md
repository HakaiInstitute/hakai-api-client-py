# Hakai API Python Client

This project exports a single Python class that can be used to make HTTP requests to the
Hakai API resource server.
The exported `Client` class extends the functionality of the
Python [requests library](https://docs.python-requests.org/en/master/) to supply Hakai
OAuth2 credentials with url requests.

[![PyPI](https://img.shields.io/pypi/v/hakai-api)](https://pypi.org/project/hakai_api/) [![tests](https://github.com/HakaiInstitute/hakai-api-client-py/actions/workflows/test.yaml/badge.svg)](https://github.com/HakaiInstitute/hakai-api-client-py/actions/workflows/test.yaml)  [![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](https://opensource.org/licenses/MIT)

**Documentation: <https://hakai-api-client-py.readthedocs.io/>**

## Installation

Python 3.11 or higher is required.

```bash
pip install hakai-api
```

## Quickstart

```python
from hakai_api import Client

# Get the api request client
client = Client()  # Follow stdout prompts to get an API token

# Make a data request for chlorophyll data (using relative endpoint)
response = client.get('/eims/views/output/chlorophyll?limit=50')

print(response.json())
# [{'action': '', 'event_pk': 7064, 'rn': '1', 'date': '2012-05-17', 'work_area': 'CALVERT'...
```

See the [documentation](https://hakai-api-client-py.readthedocs.io/) for the desktop OAuth flow,
credential management, user agent configuration, custom API roots, and the full API reference. For
the available endpoints, see the [Hakai API documentation](https://hakaiinstitute.github.io/hakai-api/).

## Contributing

See [CONTRIBUTING](CONTRIBUTING.md)

## License

See [LICENSE](LICENSE.md)
