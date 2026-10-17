#!/bin/sh
# Show the phone and keep the demo turn stub up. Run from a Pi desktop session.
set -e

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
mkdir -p "$HOME/.omni"

if ! python3 -c 'import socket; socket.create_connection(("127.0.0.1", 8787), 1).close()' 2>/dev/null; then
  python3 "$ROOT/cloud/stub_server.py" >> "$HOME/.omni/stub.log" 2>&1 &
fi

# A closed window comes back. Ctrl+Shift+Q and --stop leave it down.
while true; do
  set +e
  python3 "$ROOT/firmware/phone.py" --kiosk
  code=$?
  set -e
  if [ "$code" -ne 2 ]; then
    exit "$code"
  fi
  echo "Phone closed; opening it again."
  sleep 0.5
done
