# Frontend Build Stage
FROM oven/bun:latest AS frontend-build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY vite.config.ts tsconfig.json index.html ./
COPY src ./src
COPY public ./public
COPY styles ./styles
RUN bun run build

# Backend and Final Stage
FROM python:3.10-slim-bookworm
LABEL maintainer="rlane@ryandlane.com"

WORKDIR /srv/confidant

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock /srv/confidant/
RUN pipenv install --system --deploy

COPY --from=frontend-build /app/dist /srv/confidant/dist
COPY . /srv/confidant/

ENV STATIC_FOLDER=../dist

EXPOSE 80

CMD ["gunicorn", "confidant.wsgi:app", "--workers=2", "-k", "gevent", "--no-control-socket", "--access-logfile=-", "--error-logfile=-"]
