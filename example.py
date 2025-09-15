"""An example showing how to use the Hakai Api Python Client."""

from hakai_api import Client

if __name__ == "__main__":
    # WEB FLOW (default)
    client = Client()
    response = client.get(f"{client.api_root}/whoami")
    print(response.json())

    # DESKTOP FLOW
    client = Client(auth_flow="desktop")  # Follow the prompts in the webpage that opens
    response = client.get("/whoami")
    print(response.json())
