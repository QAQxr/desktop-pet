#!/usr/bin/env bash
set -euo pipefail

# Resolve this script's real path, following symlinks, so the project root is
# found correctly when invoked as e.g. ~/.local/bin/pet -> .../run.sh.
# Must not depend on the current working directory.
SELF="${BASH_SOURCE[0]}"
if readlink -f "$SELF" >/dev/null 2>&1; then
  SCRIPT_PATH="$(readlink -f "$SELF")"
else
  while [ -h "$SELF" ]; do
    DIR="$(cd -P "$(dirname "$SELF")" && pwd)"
    SELF="$(readlink "$SELF")"
    [[ "$SELF" != /* ]] && SELF="$DIR/$SELF"
  done
  SCRIPT_PATH="$(cd -P "$(dirname "$SELF")" && pwd)/$(basename "$SELF")"
fi
HERE="$(dirname "$SCRIPT_PATH")"
ENV_NAME="${DESKTOP_PET_ENV:-desktop-pet}"

# Resolve the conda env prefix once, then exec python directly.
# Exec'ing (rather than `conda run`) keeps the app as the foreground process,
# so closing the terminal (SIGHUP) tears the window down and leaves no orphan.
PREFIX="$(conda run -n "$ENV_NAME" python -c 'import sys; print(sys.prefix)')"

# Let Qt's xcb platform plugin find conda-provided libs (e.g. libxcb-cursor.so.0)
# without touching the system.
export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec "$PREFIX/bin/python" "$HERE/src/main.py" "$@"
