#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="${DESKTOP_PET_ENV:-desktop-pet}"

# Ensure Qt's xcb platform plugin can find conda-provided libs
# (e.g. libxcb-cursor.so.0) without touching the system.
PREFIX="$(conda run -n "$ENV_NAME" python -c 'import sys; print(sys.prefix)')"
export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec conda run --no-capture-output -n "$ENV_NAME" python "$HERE/src/main.py" "$@"
