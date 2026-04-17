#!/usr/bin/env bash
set -euo pipefail

docker compose run --rm --no-deps frontend bun run build
