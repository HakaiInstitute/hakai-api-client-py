"""An example showing how to use the Hakai Api Python Client."""

from hakai_api import Client

if __name__ == '__main__':
    # Get the api request client
    client = Client()

    # Make a data request for sampling stations
    url = '%s/%s' % (client.api_root, '/aco/views/projects/phases')
    response = client.get(url)

    print(url)
    print(response.json())
