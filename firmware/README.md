# Device shell

Desktop simulator and Raspberry Pi use the same pygame controller and 480×800 UI in `native_ui.py`. The Pi rotates it onto its 800×480 LCD. Defaults are Omni, Settings, Notes, Clock, and Calculator.

## Run

Desktop: `sh sim/run.sh`. Pi: `sh firmware/demo.sh`.

The Pi must be logged into its graphical desktop. From SSH:

```sh
cd ~/Omni
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WAYLAND_DISPLAY=wayland-0
export SDL_VIDEODRIVER=wayland
sh firmware/demo.sh
```

The first run configures the touchscreen and may reboot. Later runs launch the UI; desktop login also opens the installed autostart entry. Quit with Ctrl+Shift+Q or `python3 firmware/shell.py --stop`.

Tap the logo to browse apps. Drag, scroll, or use Up/Down to rotate the wheel; tap the selected icon or press Enter to open it. Back/Escape returns to the wheel, then home. Notes has a touchscreen keyboard, Clock supports 12/24-hour time, and Calculator accepts touch/keyboard arithmetic.

## Local speech and app generation

Install system pygame (`sudo apt install python3-pygame` on the Pi), then set up local recognition:

```sh
sudo apt install python3-venv libportaudio2
python3 -m venv --system-site-packages .venv
.venv/bin/pip install vosk==0.3.45 sounddevice==0.5.6
.venv/bin/python sim/setup_speech.py
mkdir -p ~/.omni
printf 'vosk\n' > ~/.omni/speech-mode
printf 'snd_rpi_googlevoicehat\n' > ~/.omni/audio-device
```

The last line chooses a Voice HAT by stable name; omit it or choose another input for other hardware. List inputs with `.venv/bin/python firmware/phone.py --list-audio-devices`. The launcher uses `.venv` when present and enables Vosk when its model exists; `speech-mode` can explicitly select `vosk` or `demo`.

Hold the waveform, speak, and release. Vosk streams partial hypotheses and finalizes all segments on release. Live partial transcription appears below the wordmark, stays visible while waiting, and is replaced by the animated response. App actions and navigation wait for the response to finish drawing and remain visible for 1.2 seconds. Brief PortAudio overruns warn instead of aborting; a full decoder queue still reports an error rather than submitting truncated audio. Recognition uses the native sample rate and stays on-device; the slower deferred decoding/audio-leveling experiment is not included.

App generation is selected separately:

| Backend | Behavior |
| --- | --- |
| `demo` | Local template preview, no server or API key |
| `stub` | POST to `--stub`, normally localhost:8787 |
| `gemini` | Call `cloud.try_turn.ask()` directly with the recognized text |

Save a launcher default in `~/.omni/app-backend`, or override it for a launch:

```sh
printf 'gemini\n' > ~/.omni/app-backend
sh firmware/demo.sh
# Explicit previews or HTTP integration:
sh firmware/demo.sh --backend demo
sh firmware/demo.sh --backend stub
```

For Gemini, keep `GEMINI_API_KEY` in the Pi's untracked `~/Omni/.env`; see [cloud/README.md](../cloud/README.md). A validated reply's `say` line is also spoken. ElevenLabs (`eleven_flash_v2_5`, voice `ELEVENLABS_VOICE_ID`) returns 22.05 kHz PCM, and `aplay` plays it on the PWM speaker. GPIO 13, physical pin 33, is the left channel; the same audio is copied to GPIO 12 so a speaker on either pin is audible. Set `ELEVENLABS_API_KEY` in that same `.env`.

`firmware/demo.sh` adds `dtoverlay=audremap,pins_12_13` and reboots once so analog audio leaves the headphone jack and comes out on those pins. Check the speaker before using a voice:

```sh
python3 firmware/speaker.py --beep
python3 firmware/speaker.py --say "Hello from Omni"
```

Both simulator and Pi support `--backend gemini`; `--live` remains an alias for `--backend stub` when launching `phone.py`/`sim/run.sh`. Replies are logged and applied through the same UI flow: `propose` adds and selects an app, `mutate` updates it, `say` appears on the main screen, and `navigate` opens the requested page. The configured preview wait applies only to the demo backend; real backends stop the waiting animation as soon as a response or error arrives. Backend errors also appear on-screen. When waiting ends, the logo arrows ease back to their default lengths over 280 ms; reduced motion restores them immediately.

Settings persists theme, motion, text size, preview wait, clock format. Device apps/preferences live in `~/.omni/pi-ui/`; simulator data lives in `~/.omni/simulator/`. The old `~/.omni/registry.json` is preserved.

## Edit, test, deploy

Edit on the development machine, run the simulator, and test both components:

```sh
.venv/bin/python -m unittest discover -s firmware -p 'test_*.py'
.venv/bin/python -m unittest discover -s cloud -p 'test_*.py'
```

Commit and push the combined version, then deploy that exact commit from the development machine:

```sh
python3 firmware/deploy.py omni@100.124.54.78 --backend gemini
python3 firmware/deploy.py omni@100.124.54.78 --verify
```

The Pi is an SCP deployment, not a Git checkout. The deployer requires clean tracked files, archives only the commit, backs up overwritten source, preserves `.env`, models, virtual environment and device data, removes retired browser simulator files, runs both test suites on the Pi, verifies file hashes, and restarts the display. Failed tests restore the previous source and relaunch it. `.omni-deployed.json` records the commit and managed file hashes. `--verify` checks the deployed source without restarting it. Development-only untracked folders are excluded. Avoid editing deployed source directly; bring any emergency fixes back into the repository before deploying again.

Hardware setup remains in [bringup/](bringup/); `--turn left` supports the opposite mounting orientation. Simulator controls are in [sim/README.md](../sim/README.md).

Generated apps now use the [v2 component contract](../contract/README.md). Components share typed state and approved actions; voice navigation can open Settings, the main agent view, the app wheel, or an existing generated app without creating anything. Validated intent metadata is saved in `last_turn`. Existing template apps migrate with a backup when the profile opens. Install `cloud/requirements.txt` into the project virtual environment before running this version; the deployer installs it automatically.
