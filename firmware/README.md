# Device shell

Omni uses one pygame UI on desktop and the Raspberry Pi 3B. The 5" LCD is 480×800 upright, rotated onto the 800×480 glass on the Pi. UI and controller code lives in `native_ui.py`; `phone.py` handles the window, display rotation, touch events, and existing JSON app widgets.

Desktop simulator:

```sh
sh sim/run.sh
```

On the Pi desktop, or SSH with the desktop environment exported:

```sh
sh firmware/demo.sh
```

The first run configures the touchscreen and display mode, then reboots. Subsequent runs launch the UI. After desktop login, the installed autostart entry opens it. The graphical desktop must be running. For SSH on Wayland:

```sh
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WAYLAND_DISPLAY=wayland-0
export SDL_VIDEODRIVER=wayland
sh firmware/demo.sh
```

Tap the main logo to browse the rotating wheel. Drag along its curve to rotate it; release to snap. Tap a neighboring icon to focus it, then tap the large selected icon to open. The corner Omni branding returns home. Back/Escape returns from an app to the wheel, then home. Defaults are Omni, Settings, Notes, Clock, and Calculator. A touchscreen keyboard is available for Notes and request entry.

Holding the waveform simulates speech. It uses the entered draft, or the shopping-list demo request if empty. The bars fluctuate while listening; after release the arrows animate during a configurable 10-second delay. The local demo then creates and selects a new app on the wheel. No microphone recording or speech recognition is implemented. Both desktop and Pi use this same demo flow by default. To use the turn stub, start it and launch `python3 firmware/shell.py --kiosk --live`.

Settings persists theme, reduced motion, text size, wait time, and clock format. Device data is `~/.omni/pi-ui/`; desktop simulator data is `~/.omni/simulator/`. The old registry remains intact. Quit with Ctrl+Shift+Q or `python3 firmware/shell.py --stop`. The next desktop login opens the installed demo again.

Install pygame with `sudo apt install python3-pygame` on the Pi, or install `pygame-ce` into a virtual environment on desktop. See [`sim/README.md`](../sim/README.md) for detailed controls and tests. Mount the display right edge up; `--turn left` supports the opposite orientation. Hardware setup remains in [`bringup/`](bringup/).
