# Contributing

## Code of conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.
All contributors and participants agree to abide by its terms.

## Contributing code

### File issues in Github

In general all enhancements or bugs should be tracked via github issues before
PRs are submitted. We don't require them, but it'll help us plan and track.

When submitting bugs through issues, please try to be as descriptive as
possible. It'll make it easier and quicker for everyone if the developers can
easily reproduce your bug.

### Submit pull requests

Our only method of accepting code changes is through github pull requests.

## Development guide

This guide assumes you're using docker desktop, which includes docker, and
docker compose.

A full developer configuration is available, using compose, which uses
local dynamodb, local kms, and a local simplesamplephp. We have quick make
aliases, so it's not necessary to learn the details of docker compose.

### Starting confidant

To start: `make up`

To test code changes:

1. Make your change.
1. If you only changed Python or frontend source, keep `make up` running. The
   backend uses gunicorn `--reload` and the frontend runs the Vite dev server,
   so no image rebuild is needed.
1. If you changed container dependencies or image build inputs (for example
   `Dockerfile`, `Pipfile.lock`, frontend package metadata, or other files
   copied into the image), run `make docker_build` and then restart with
   `make up`.

If you want to force a rebuild before starting the stack, use
`make up_build`.

Confidant will be accessible at `http://localhost`. The username is `confidant`
and the password is `confidant`.

All configuration settings for this environment are in the `config/development`
directory. If you wish to change any settings, kill the docker compose, make the
change, and start the docker compose environment back up.

The development environment defaults `AUDIT_LOG_LEVEL=WARNING` in
`config/development/confidant.env` so audit events stand out from routine
request logging.

### Running tests

The easiest way to run the tests is through docker compose as well, as both unit
and integration test suites can be run via compose.

To run the full test suite (minus pre-commit):

```bash
# See the target in the make file; this runs build, unit, integration and down
make docker_test
```

To run only unit tests:

```bash
make docker_build
make docker_test_unit
```

To run only integration tests:

```bash
make docker_build
make docker_test_integration
```

To run only frontend tests:

```bash
make docker_build
make docker_test_frontend
```

Lint tests are through pre-commit, so it's necessary to [install/run precommit](https://pre-commit.com/#install)
first. To run pre-commit:

```bash
pre-commit run --all-files
```

If you want to have pre-commit auto-run when committing:

```bash
pre-commit install
```
