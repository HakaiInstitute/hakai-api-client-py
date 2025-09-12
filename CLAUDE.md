# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Hakai API Python Client is a Python library that provides a client for making authenticated HTTP requests to the Hakai API resource server. It extends the functionality of the Python requests library to supply Hakai OAuth2 credentials with URL requests.

## Commands

### Installation and Setup

```bash
# Install dependencies with uv (project has transitioned from Poetry)
uv sync

# Setup pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_Client.py

# Run a specific test function
pytest tests/test_Client.py::test_get_valid_credentials_from_file
```

### Linting

```bash
# Run the Ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Auto format code
ruff format .
```

## Architecture

The project has a simple architecture with a single core class:

- `Client` (in `src/hakai_api/Client.py`): Extends `OAuth2Session` from the `requests_oauthlib` library to handle OAuth2 authentication with the Hakai API. It manages credential persistence and OAuth2 token handling.

Key features of the `Client` class:
- Handles authentication via web login, environment variables, or cached credentials
- Stores credentials in `~/.hakai-api-auth`
- Provides access to the API endpoints via standard HTTP methods (get, post, etc.)
- Offers configurable API root URL and login pages

## Development Workflow

1. Make changes to the code
2. Run tests to ensure functionality
3. Run lint checks
4. Create a pull request
5. When ready for release, create a git tag following the pattern `v[0-9]+.[0-9]+.[0-9]+` to trigger automatic deployment via GitHub Actions
