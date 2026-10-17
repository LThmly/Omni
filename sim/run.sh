#!/bin/sh
# Launch the real pygame UI with a separate simulator profile.
set -eu
omni_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
if [ -x "$omni_root/.venv/bin/python" ]; then
    omni_python="$omni_root/.venv/bin/python"
else
    omni_python=python3
fi
exec "$omni_python" "$omni_root/sim/run.py" "$@"
