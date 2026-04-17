#!/usr/bin/env bash
set -euo pipefail

source_dir=${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
dest_dir=${2:-/tmp/confidant-compose-context}

rm -rf "$dest_dir"
mkdir -p "$dest_dir"

rsync -a --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'gunicorn.ctl' \
  "$source_dir"/ "$dest_dir"/
