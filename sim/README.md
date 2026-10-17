# Pygame simulator

Run the same UI as the Pi, upright at 480×800:

```sh
sh sim/run.sh
```

The launcher uses the project's `.venv` if present, otherwise `python3`. For a new desktop checkout:

```sh
python3 -m venv .venv
.venv/bin/pip install -r sim/requirements.txt
sh sim/run.sh
```

On the Pi, `python3-pygame` from apt also works. The simulator uses `firmware/native_ui.py`, the same renderer, controller, and app logic as `python3 firmware/shell.py --kiosk`. A mouse press/drag/release follows the same path as a finger on the Pi. The earlier browser studies are design references; edit the pygame files to change the real UI.

- Tap the logo to open the wheel; drag around its curve, scroll, or use Up/Down to select. Tap the selected app or press Enter to open it. Tap a neighboring icon to rotate it into focus.
- Tap the corner Omni mark to go home. Back/Escape returns from an app to the wheel, then home. Ctrl+Shift+Q quits.
- Defaults: Omni, Settings, Notes, Clock, Calculator. Settings persists theme, reduced motion, text size, simulated wait, and clock format.
- Hold the waveform for at least 350 ms to simulate speech release. The bars fluctuate while held, then the arrows animate for 10 seconds (configurable), and a generated app appears selected on the wheel. Cancel a held gesture by changing window focus; Escape cancels a pending request.
- Type a request on desktop and press Enter, or use the small keyboard symbol on the home screen to enter it with touch. Without a draft, speech simulation requests a shopping list. Microphone recording and speech recognition are not implemented.
- Notes supports physical typing and an on-screen keyboard. Clock updates from the computer's local clock. Calculator accepts touch/keyboard arithmetic.
- Ctrl+D restores the five defaults, clearing generated apps and notes in the active profile.

The simulator stores apps and preferences under `~/.omni/simulator/`; the Pi uses `~/.omni/pi-ui/`. The earlier `~/.omni/registry.json` is preserved. Use `--store /path/to/registry.json` for another profile. Nothing needs a server in the default demo mode.

For real stub requests:

```sh
python3 cloud/stub_server.py
sh sim/run.sh --live
```

`--live` uses `--stub` (default `http://127.0.0.1:8787/v1/turn`) and waits at least the configured delay before applying the reply. Only generated apps are sent in the registry. A proposal is saved and selected on the wheel; a mutation selects the affected app. Failed calls return to the agent screen with a message.

Stop a running simulator with `sh sim/run.sh --stop`. Device stop uses `python3 firmware/shell.py --stop`. Their process locks are separate.

Tests (no display required):

```sh
python3 -m unittest discover -s firmware -p 'test_*.py'
```
