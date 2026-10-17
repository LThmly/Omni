#!/bin/sh
# Register the phone so Raspberry Pi OS opens it at every login.
# The desktop stays underneath. The app stays in front until you quit it.
set -e

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PYTHON=$(command -v python3)
MODEL=""
if [ -r /proc/device-tree/model ]; then
  MODEL=$(tr -d '\0' < /proc/device-tree/model)
fi
case "$MODEL" in
  *Raspberry\ Pi*) ;;
  *)
    echo "Run this on the Pi. It opens the phone at login."
    exit 1
    ;;
esac

if ! command -v chromium >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser
fi

mkdir -p "$HOME/.config/autostart" "$HOME/.config/labwc" "$HOME/.omni"

cat > "$HOME/.config/autostart/omni.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Omni
Comment=Portrait Omni phone
Exec=$PYTHON $ROOT/firmware/shell.py --kiosk
X-GNOME-Autostart-enabled=true
EOF

AUTOSTART="$HOME/.config/labwc/autostart"
touch "$AUTOSTART"
if ! grep -q "firmware/shell.py" "$AUTOSTART"; then
  printf '\n# omni\n%s %s/firmware/shell.py --kiosk &\n' "$PYTHON" "$ROOT" >> "$AUTOSTART"
fi

echo "Installed. Log out and back in, or reboot."
echo "The phone opens over the desktop and stays there."
echo "Stand the stack so its right edge is up."
echo "If the UI is upside down, change --kiosk to --kiosk --turn left in:"
echo "  $HOME/.config/autostart/omni.desktop"
echo "  $AUTOSTART"
echo "Quit with Ctrl+Shift+Q, or: $PYTHON $ROOT/firmware/shell.py --stop"
