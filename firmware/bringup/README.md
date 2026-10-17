# On the Pi

From a terminal on the desktop:

```bash
sh firmware/demo.sh
```

The first run adds the XPT2046 overlay and `video=HDMI-A-1:800x480M@60`, then reboots. Log in. The phone is on the glass.

Seat the display on the 40-pin header and connect the Pi’s HDMI port before that reboot. Pin names are in [`context/hardware.md`](../../context/hardware.md). If a sideways drag moves the pointer up and down, set `swapxy=1` on the `ads7846` line in `/boot/firmware/config.txt` and reboot. Do not set `display_rotate`.

Stand the stack so the right edge of the landscape picture is up. If the phone is upside down, change `--kiosk` to `--kiosk --turn left` in `firmware/start-demo.sh`.

Quit with Ctrl+Shift+Q, or:

```bash
python3 firmware/shell.py --stop
```

The next login opens it again.
