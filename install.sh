#!/usr/bin/env sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.11+ is required. Install python3 with your package manager first.' >&2
  exit 1
fi
exec python3 "$root/setup.py" "$@"
