#!/bin/sh
# Show the phone and keep the demo turn stub up. Run from a Pi desktop session.
set -e

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
mkdir -p "$HOME/.omni"

if ! python3 -c 'import socket; socket.create_connection(("127.0.0.1", 8787), 1).close()' 2>/dev/null; then
  python3 "$ROOT/cloud/stub_server.py" >> "$HOME/.omni/stub.log" 2>&1 &
fi

exec python3 "$ROOT/firmware/shell.py" --kiosk
