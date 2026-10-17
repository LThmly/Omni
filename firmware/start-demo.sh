#!/bin/sh
# Show the phone and keep the demo turn stub up. Run from a Pi desktop session.
set -e

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
mkdir -p "$HOME/.omni"
PYTHON=python3
if [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
fi
SPEECH=demo
if [ -f "$ROOT/sim/models/vosk-model-small-en-us-0.15/am/final.mdl" ]; then
  SPEECH=vosk
fi
if [ -r "$HOME/.omni/speech-mode" ]; then
  SPEECH=$(cat "$HOME/.omni/speech-mode")
fi
BACKEND=demo
if [ -r "$HOME/.omni/app-backend" ]; then
  BACKEND=$(cat "$HOME/.omni/app-backend")
fi
set -- --kiosk --speech "$SPEECH" --backend "$BACKEND" "$@"
if [ -r "$HOME/.omni/audio-device" ]; then
  set -- "$@" --audio-device "$(cat "$HOME/.omni/audio-device")"
fi

if [ "$BACKEND" = stub ] && ! "$PYTHON" -c 'import socket; socket.create_connection(("127.0.0.1", 8787), 1).close()' 2>/dev/null; then
  "$PYTHON" "$ROOT/cloud/stub_server.py" >> "$HOME/.omni/stub.log" 2>&1 &
fi

# A closed window comes back. Ctrl+Shift+Q and --stop leave it down.
while true; do
  set +e
  "$PYTHON" -u "$ROOT/firmware/phone.py" "$@"
  code=$?
  set -e
  if [ "$code" -ne 2 ]; then
    exit "$code"
  fi
  echo "Phone closed; opening it again."
  sleep 0.5
done
