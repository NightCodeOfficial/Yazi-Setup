#!/usr/bin/env sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.11+ is required. Install python3 with your package manager first.' >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo 'Python 3.11+ is required. Upgrade python3 with your package manager first.' >&2
  exit 1
fi
# Match the Windows double-click installer. Use --configure-only for an existing
# installation, or the read-only --check-previews mode for diagnostics.
case "${1-}" in
  --configure-only) shift ;;
  --check-previews|--help|-h) ;;
  *) set -- --install-yazi --install-dependencies --theme choose "$@" ;;
esac
exec python3 "$root/setup.py" "$@"
