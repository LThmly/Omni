# On the Pi

The panel is a 5" 800×480 HDMI LCD. Touch is the XPT2046 on the GPIO header. Picture and touch are set up once, then the phone opens at every login. Pin names and the exact lines are in [`context/hardware.md`](../../context/hardware.md).

1. Seat the display on the 40-pin header and connect HDMI to the Pi’s full-size HDMI port.
2. In `/boot/firmware/config.txt`, add the `ads7846` overlay from the hardware notes. That is the touchscreen.
3. Append `video=HDMI-A-1:800x480M@60` to the single line in `/boot/firmware/cmdline.txt`.
4. Reboot. The desktop should fill the glass, and a finger should move the pointer. If a sideways drag moves the pointer vertically, set `swapxy=1` in the overlay and reboot. Do not set `display_rotate`.

## Touch Diagnostics & Bringup

Before launching the full shell, verify the touchscreen driver, axis alignment, and calibration:

- **Configuration & Device Check:**
  ```bash
  python3 firmware/bringup/test_display_touch.py --check
  ```
- **Visual Touch Calibration Test (Fullscreen GUI):**
  ```bash
  python3 firmware/bringup/test_display_touch.py
  ```
  Tap the 5 targets (4 corners + center) to verify coordinate scaling and check for axis inversion. Press `c` to clear, `q` or `ESC` to quit.
- **CLI Event Monitor (Terminal):**
  ```bash
  python3 firmware/bringup/test_display_touch.py --cli
  ```
- **Browser Touch Test:**
  Open `firmware/bringup/test_screen.html` in Chromium to test browser pointer events, touch latency, and rotation.

5. From the repo:

   ```bash
   python3 firmware/install.sh
   ```

   Log out and back in, or reboot. The phone opens over the desktop and stays there. Closing the window opens it again.

Stand the stack so the right edge of the landscape picture is up. The app is a 480×800 phone turned onto the glass. If it comes up upside down, change `--kiosk` to `--kiosk --turn left` in `~/.config/autostart/omni.desktop` and `~/.config/labwc/autostart`, then log in again.

Quit with Ctrl+Shift+Q, or from a shell:

```bash
python3 firmware/shell.py --stop
```

The next login opens it again.
