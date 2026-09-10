#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="${DESKTOP_PET_ENV:-desktop-pet}"
exec conda run --no-capture-output -n "$ENV_NAME" python "$HERE/src/main.py" "$@"
