# Frontend Build Stage
FROM oven/bun:latest AS frontend-build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY vite.config.js ./
COPY confidant/public ./confidant/public
RUN bun run build

# Backend and Final Stage
FROM ubuntu:jammy
LABEL maintainer="rlane@ryandlane.com"

WORKDIR /srv/confidant

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl ca-certificates python3.10 python3-pip python3.10-dev gcc pkg-config \
        libffi-dev libxml2-dev libxmlsec1-dev git-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock /srv/confidant/
RUN pipenv install --system --deploy

COPY --from=frontend-build /app/confidant/dist /srv/confidant/confidant/dist
COPY . /srv/confidant/

ENV STATIC_FOLDER=dist

EXPOSE 80

CMD ["gunicorn", "confidant.wsgi:app", "--workers=2", "-k", "gevent", "--access-logfile=-", "--error-logfile=-"]
