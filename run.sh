#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="${DESKTOP_PET_ENV:-desktop-pet}"

# Resolve the conda env prefix once, then exec python directly.
# Exec'ing (rather than `conda run`) keeps the app as the foreground process,
# so closing the terminal (SIGHUP) tears the window down and leaves no orphan.
PREFIX="$(conda run -n "$ENV_NAME" python -c 'import sys; print(sys.prefix)')"

# Let Qt's xcb platform plugin find conda-provided libs (e.g. libxcb-cursor.so.0)
# without touching the system.
export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec "$PREFIX/bin/python" "$HERE/src/main.py" "$@"
