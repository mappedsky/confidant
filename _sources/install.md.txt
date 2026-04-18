# Installation
## Quickstart for testing

If you just want to checkout Confidant and aren't looking to deploy it into
production, it's possible to get started without any external dependencies.
Check out the [test and development quickstart](contributing.md#development-guide)
for this.

Note that you should _never_ run with this quickstart configuration in production.

## Docker installation

### To run confidant in Docker

It's necessary to export your configuration variables before running confidant.
You can either specify them as multiple -e options, or you can put them into
an environment file and use --env-file.

A production-ready docker image is available in
[GitHub Container Registry](https://github.com/mappedsky/confidant/pkgs/container/confidant).

```bash
docker pull ghcr.io/mappedsky/confidant:master
```

This image can then be ran with any of your desired command line flags:

```bash
docker run --rm ghcr.io/mappedsky/confidant:master --help
```

### To build the image

If you want to build the image and store it in your private registry, you can
do the following:

```bash
git clone https://github.com/mappedsky/confidant
cd confidant
docker build -t mappedsky/confidant .
```

## Local installation (Manual)

Assumptions:

1. Using Python 3.10+
1. Using Bun for frontend builds
1. Using pipenv for dependency management

### Clone Confidant

```bash
cd /srv
git clone https://github.com/mappedsky/confidant
```

### Install Python dependencies

```bash
cd /srv/confidant
pip install pipenv
pipenv install
```

### Build the frontend

```bash
cd /srv/confidant
# Install bun (see https://bun.sh)
bun install
bun run build
```

### Run confidant

It's necessary to export your configuration variables before running confidant.
The easiest method is to source a file that exports your environment before
running confidant.

```bash
source my_config
cd /srv/confidant
pipenv run gunicorn confidant.wsgi:app --workers=2 -k gevent
```

That's it. See the configuration documentation about how to configure and run.
