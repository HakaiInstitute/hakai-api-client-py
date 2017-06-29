# Hakai Api Python Client

This project exports a single Python class that can be used to make HTTP requests
to the Hakai API resource server. The Class extends the functionality of the popular
Python requests library so that OAuth2 configuration is completed without needing to
know the details. All methods available on the requests.Session class are
available in this class, so for specifics about how to make requests, the requests documentation should be consulted.

## Quickstart

Install the package with Pip
```bash
pip install --upgrade git@ssh://git@github.com:HakaiInstitute/hakai-data-tools.git@development#egg=hakai_api&subdirectory=/tree/development/api-data-request/python/hakai_api

```
