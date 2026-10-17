# Pygame simulator

Run the same UI as the Pi, upright at 480×800:

```sh
sh sim/run.sh
```

The launcher uses the project's `.venv` if present, otherwise `python3`. For a new desktop checkout:

```sh
python3 -m venv .venv
.venv/bin/pip install -r sim/requirements.txt
.venv/bin/python sim/setup_speech.py
sh sim/run.sh
```

On the Pi, `python3-pygame` from apt also works. The simulator uses `firmware/native_ui.py`, the same renderer, controller, and app logic as `python3 firmware/shell.py --kiosk`. A mouse press/drag/release follows the same path as a finger on the Pi. Edit the pygame files to change the UI.

- Tap the logo to open the wheel; drag around its curve, scroll, or use Up/Down to select. Tap the selected app or press Enter to open it. Tap a neighboring icon to rotate it into focus.
- Tap the corner Omni mark to go home. Back/Escape returns from an app to the wheel, then home. Ctrl+Shift+Q quits.
- Defaults: Omni, Settings, Notes, Clock, Calculator. Settings persists theme, reduced motion, text size, simulated wait, clock format, and Live input visibility.
- Hold the waveform, speak into the microphone, and release to submit. Vosk updates the prompt as words are recognized, revises partial hypotheses, and flushes the final transcript on release. The bars fluctuate while held; afterward the arrows animate during generation and the new app appears selected. Gestures under 350 ms, cancelled gestures, microphone errors, and silence never submit a fake/default request. Escape or a focus change cancels capture.
- Live input appears under the main wordmark and the submitted request stays visible during the wait. New words fade in over about 160 ms, each line stays centered with eased position changes, and recognition corrections blend only the changed words. Long input scrolls smoothly to its latest two lines. Reduced motion makes updates immediate. **Settings → Live input** hides the visual without changing recognition or what is sent.
- You can still type a request and press Enter, or enter one with the on-screen keyboard. While microphone capture is active, transcription owns the prompt and keyboard edits are ignored.
- Notes supports physical typing and an on-screen keyboard. Clock updates from the computer's local clock. Calculator accepts touch/keyboard arithmetic.
- Ctrl+D restores the five defaults, clearing generated apps and notes in the active profile.

The simulator stores apps and preferences under `~/.omni/simulator/`; the Pi uses `~/.omni/pi-ui/`. The earlier `~/.omni/registry.json` is preserved. Use `--store /path/to/registry.json` for another profile. Speech recognition runs locally with Vosk. App generation still uses the local demo templates and a configurable 10-second wait by default; no server is required.

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

## Microphone setup

`sh sim/run.sh` now defaults to real Vosk recognition. `setup_speech.py` downloads the official `vosk-model-small-en-us-0.15` model (about 40 MB) into ignored `sim/models/`. It is loaded once at startup and recognition then works offline. PortAudio must be installed: Arch uses `portaudio`, Debian/Pi uses `libportaudio2`.

List inputs or choose a microphone by index/name:

```sh
sh sim/run.sh --list-audio-devices
sh sim/run.sh --audio-device 6
sh sim/run.sh --audio-device pipewire
sh sim/run.sh --model /path/to/unpacked-vosk-model
```

The system's default input is used unless overridden. Audio is mono 16-bit PCM at the input's native sample rate. Capture and decoding run on a worker thread; results are applied on the pygame thread. Releasing stops capture, drains the queued audio, and submits Vosk's final text. Multiple finalized segments across pauses are retained. Audio is not saved to disk.

For the earlier animation-only demonstration, explicitly use `sh sim/run.sh --speech demo`. The Pi retains that mode by default; enable microphone recognition there with `python3 firmware/shell.py --kiosk --speech vosk` after installing the requirements and model on the Pi. `--live` controls the app-generation backend independently of `--speech`.

References: [Vosk microphone example](https://github.com/alphacep/vosk-api/blob/master/python/example/test_microphone.py), [official models](https://alphacephei.com/vosk/models).
