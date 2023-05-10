# Contributing

This document describes how to set up a development environment for this project, modify
and test the code, and deploy a new version.

<details>

<summary>Table of Contents</summary>

[Project structure](#project-structure)

[Configuration](#configuration)

[Tests](#tests)

[Deployment](#deployment)

</details>

## Project structure

The business logic for this package is located
in [`hakai_api/Client.py`](hakai_api/Client.py).
All tests are located in the `tests/` directory.

## Configuration

### Poetry

This project uses [Poetry](https://python-poetry.org/) for dependency management and
packaging. Install Poetry using the instructions on their website before continuing.

To set up an environment for development, clone this repository and run the following
commands from the root directory of the repository:

```bash
# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

### Pre-commit

This project uses [pre-commit](https://pre-commit.com/) to run lint checks and tests
before every commit. To install the pre-commit hooks, run the following command from the
root directory of the repository while the virtual environment is active, after
installing Poetry:

```bash
pre-commit install
```

This is highly recommended and will prevent failed builds on GitHub Actions, as well as
ensure consistent code style and quality.

## Tests

Tests and lint checks are automatically run on pull requests and pushes to the main
branch
using GitHub Actions.

To run the tests locally, run the following command from the root directory of the
repository
while the virtual environment is active:

```bash
pytest
```

## Deployment

To build and deploy a new PyPi package version, push a tag matching the
pattern `v[0-9]+.[0-9]+.[0-9]+` or `v[0-9]+.[0-9]+.[0-9]+rc[0-9]+` (e.g. `v0.4.1`
or `v0.5.2rc1`) to GitHub. GitHub Actions will take care of packaging and pushing it
to Hakai's PyPi repository from there.

Under the hood, the GitHub Action uses Poetry to build the package and Twine to upload
it to PyPi. The PyPi repository is configured in the `pyproject.toml` file.