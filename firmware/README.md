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

In the desktop simulator, holding the waveform records the system microphone through Vosk. Partial results update the prompt while speaking; release stops capture, flushes the final transcript, and begins generation. Recognition is offline after downloading the model with `.venv/bin/python sim/setup_speech.py`. Install speech dependencies from `sim/requirements.txt`; the Linux audio dependency is PortAudio (`portaudio` on Arch, `libportaudio2` on Debian/Pi). Use `sh sim/run.sh --list-audio-devices` and `--audio-device` to select an input.

The Pi still defaults to the scripted speech preview until a microphone is configured. To enable real ASR there, install the same dependencies/model and run `python3 firmware/shell.py --kiosk --speech vosk`. Use `--speech demo` for the earlier timed partial-transcript animation. App generation is a local template demo with a configurable 10-second wait by default in either speech mode. To use the turn stub, start it and add `--live`.

Settings persists theme, reduced motion, text size, wait time, clock format, and Live input visibility. Live input shows entered/simulated speech under the main wordmark and retains the submitted request while waiting. Settings → Live input hides or shows it without changing the request. Device data is `~/.omni/pi-ui/`; desktop simulator data is `~/.omni/simulator/`. The old registry remains intact. Quit with Ctrl+Shift+Q or `python3 firmware/shell.py --stop`. The next desktop login opens the installed demo again.

Install pygame with `sudo apt install python3-pygame` on the Pi, or install `pygame-ce` into a virtual environment on desktop. See [`sim/README.md`](../sim/README.md) for detailed controls and tests. Mount the display right edge up; `--turn left` supports the opposite orientation. Hardware setup remains in [`bringup/`](bringup/).
