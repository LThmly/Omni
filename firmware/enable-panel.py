#!/usr/bin/env python3
"""Turn on the 5" panel and the XPT2046 touchscreen.

Prints "reboot" when /boot was changed, otherwise "ready".
Run with sudo on the Pi.
"""

import sys
from pathlib import Path

OVERLAY = (
    "dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,"
    "keep_vref_on=1,swapxy=0,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900"
)
VIDEO = "video=HDMI-A-1:800x480M@60"
I2S_LINES = [
    "dtparam=i2s=on",
    "dtoverlay=googlevoicehat-soundcard",
]
# BCM GPIO 13 (physical pin 33) is the left PWM channel. GPIO 12 is the right.
AUDIO_LINES = [
    "dtparam=audio=on",
    "dtoverlay=audremap,pins_12_13",
]
# BCM GPIO 21 (physical pin 40) stays an output driven low.
GPIO_LOW_LINES = [
    "gpio=21=op,dl",
]


def first_existing(paths):
    for path in paths:
        if path.exists():
            return path
    return None


def main():
    config = first_existing((Path("/boot/firmware/config.txt"), Path("/boot/config.txt")))
    cmdline = first_existing((Path("/boot/firmware/cmdline.txt"), Path("/boot/cmdline.txt")))
    if config is None or cmdline is None:
        print("No boot config found. Run this on the Pi.", file=sys.stderr)
        return 1

    changed = False
    text = config.read_text()
    to_add = []
    if "dtoverlay=ads7846" not in text:
        to_add.append(OVERLAY)
    for entry in I2S_LINES + AUDIO_LINES + GPIO_LOW_LINES:
        if entry not in text:
            to_add.append(entry)

    if to_add:
        if text and not text.endswith("\n"):
            text += "\n"
        config.write_text(text + "\n".join(to_add) + "\n")
        changed = True

    line = cmdline.read_text().replace("\n", "")
    if "800x480" not in line:
        cmdline.write_text(line.rstrip() + " " + VIDEO + "\n")
        changed = True

    print("reboot" if changed else "ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
