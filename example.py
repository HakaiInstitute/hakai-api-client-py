#!/usr/bin/python3
"""An example showing how to use the Hakai Api Python Client."""

from hakai_api import Client


# Get the api request client
client = Client()

# Make a data request for sampling stations
url = '%s/%s' % (client.api_root, 'eims/views/station_matrix?limit=-1&fields=project_name,project_pk&distinct')
response = client.get(url)

print(url)
print(response.json())
