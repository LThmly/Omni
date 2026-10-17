#!/bin/sh
# One shot on the Pi: wire the touchscreen, then open the demo.
# After the first reboot, login opens the same demo again.
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
    echo "Run this on the Pi, from a desktop terminal."
    exit 1
    ;;
esac

if ! "$PYTHON" -c "import pygame" >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3-pygame
fi

if ! command -v arecord >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y alsa-utils
fi

mkdir -p "$HOME/.config/autostart" "$HOME/.config/labwc" "$HOME/.omni"

cat > "$HOME/.config/autostart/omni.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Omni
Comment=Omni touch demo
Exec=$ROOT/firmware/start-demo.sh
X-GNOME-Autostart-enabled=true
EOF

AUTOSTART="$HOME/.config/labwc/autostart"
touch "$AUTOSTART"
if ! grep -q "firmware/start-demo.sh" "$AUTOSTART"; then
  printf '\n# omni\n%s &\n' "$ROOT/firmware/start-demo.sh" >> "$AUTOSTART"
fi

chmod +x "$ROOT/firmware/start-demo.sh" "$ROOT/firmware/demo.sh"

RESULT=$(sudo "$PYTHON" "$ROOT/firmware/enable-panel.py")
if [ "$RESULT" = "reboot" ]; then
  echo "Touchscreen driver and 800x480 mode are saved."
  echo "Rebooting. After you log in, the demo opens on the panel."
  sudo reboot
fi

echo "Panel already configured. Opening the demo."
exec "$ROOT/firmware/start-demo.sh"
