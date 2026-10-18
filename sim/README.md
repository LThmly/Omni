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
- Defaults: Omni, Settings, Notes, Clock, Calculator. Settings persists theme, reduced motion, text size, simulated wait, clock format.
- Hold the waveform, speak into the microphone, and release to submit. Vosk displays live partial hypotheses and flushes the final transcript on release. The bars fluctuate while held; afterward the arrows animate during generation and the new app appears selected. Gestures under 350 ms, cancelled gestures, microphone errors, and silence never submit a fake/default request. Escape or a focus change cancels capture.
- Live speech appears beneath the wordmark as Vosk updates its partial hypotheses; the submitted text remains while waiting. Responses replace it with a centered, progressive word reveal. Both use soft fades and smooth corrections. Speech previews retain three lines; replies target 2–6 words and fit one line. When the response arrives, all logo arrows ease back to their default lengths over 280 ms; reduced motion resets them immediately.
- You can still type a request with a physical keyboard and press Enter. The main screen has no on-screen keyboard button. While microphone capture is active, transcription owns the prompt and keyboard edits are ignored.
- Notes supports physical typing and an on-screen keyboard. Clock updates from the computer's local clock. Calculator accepts touch/keyboard arithmetic.
- Ctrl+D restores the five defaults, clearing generated apps and notes in the active profile.
- Settings → Delete generated apps asks for confirmation, removes generated apps, and preserves the five defaults, Notes, and preferences.

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

The system's default input is used unless overridden. Audio is mono 16-bit PCM at the input's native sample rate. Capture and decoding run on a worker thread; results are applied on the pygame thread. Releasing stops capture, drains the queued audio, and submits Vosk's final text. Multiple finalized segments across pauses are retained. Empty provisional results leave the current preview visible, and queued partials continue updating it after release until the final transcript arrives. Speech/request previews show the latest three lines; agent responses are fitted to one line, with a word-aware ellipsis if needed. Audio is not saved to disk.

To try the larger streaming English model locally:

```sh
.venv/bin/python sim/setup_speech.py --model accurate
sh sim/run.sh --stop
sh sim/run.sh --backend gemini --model sim/models/vosk-model-en-us-0.22-lgraph
```

This downloads the official 128 MB `vosk-model-en-us-0.22-lgraph`. It runs offline and supports live partial results. The [official model table](https://alphacephei.com/vosk/models) reports lower error rates than the default small model on its English test sets; this does not guarantee better recognition for every voice or microphone. The choice is explicit per launch: omitting `--model` still uses the small model.

On the development computer, decoding the official Vosk example's 8.31-second recording in 100 ms chunks took 3.49 seconds with the larger model versus 0.87 seconds with the small model. Peak process memory was approximately 477 MiB versus 218 MiB. These are single-sample development measurements, not Pi benchmarks or representative accuracy tests. Keep the Pi 3 on the small model until the larger model's speed and total system memory usage have been measured there. Return to the default with `sh sim/run.sh --backend gemini` after stopping the simulator.

For the earlier animation-only demonstration, explicitly use `sh sim/run.sh --speech demo`. The Pi retains that mode by default; enable microphone recognition there with `python3 firmware/shell.py --kiosk --speech vosk` after installing the requirements and model on the Pi. `--live` controls the app-generation backend independently of `--speech`.

References: [Vosk microphone example](https://github.com/alphacep/vosk-api/blob/master/python/example/test_microphone.py), [official models](https://alphacephei.com/vosk/models).

## Shared backends and deployment

`sh sim/run.sh --backend gemini` calls the same Gemini client as the Pi using a local untracked `.env`. `--backend demo` keeps template generation local; `--backend stub` (or `--live`) uses the HTTP server. All replies go through the shared app controller, so generated apps, mutations, and messages appear on-screen. Live local transcription and responses share the same centered text animation. Navigation, app creation, and app edits wait until the response finishes drawing, followed by a 1.2-second reading pause; Escape cancels a queued action. The Pi deployment workflow and commit verification are documented in [firmware/README.md](../firmware/README.md#edit-test-deploy).

## Component apps and navigation

The shared [v2 response contract](../contract/README.md) classifies messages, app creation, app edits, and navigation. Try `Take me to settings` or `Take me to the main agent view`. Real requests use Gemini; the offline demo supports these explicit navigation commands too. Generated apps use only fixed components and shared typed state. Tap an input to edit it; buttons execute declared actions locally without a model call. Old generated templates are migrated with a profile backup. Install the updated `sim/requirements.txt` to include JSON Schema validation.

App screens slide in from the selector and slide back when dismissed. Voice navigation starts the selector at the app farthest from the target, rotates to the requested app, then opens it. Reduced motion skips these animations; Escape cancels an in-progress voice navigation at the selector.

Complete navigation commands such as “Navigate to the settings page”, “Please open my notes app”, “Take me to the main agent view”, and “Go back to the app selection screen” run locally after Vosk finalizes speech, without an API call. Exact existing generated app names work too. Ambiguous names, unknown pages, questions, and combined commands fall through to Gemini.

Voice theme commands also run locally: “Switch to light mode”, “Enable dark mode”, “Set the theme to light mode”, or “Toggle the theme”. Omni displays its animated acknowledgment before applying and saving the theme. Escape cancels the pending change.

The expanded [local voice command catalog](VOICE_COMMANDS.md) covers navigation aliases, themes, motion, text size, clock format, time/date answers, notes, spoken arithmetic, and actions/list additions in existing generated apps. These bypass the backend and use the same response-before-action flow.

See the [generated-app layout and workflow guide](../docs/GENERATED_APPS.md) for real app pages, consistent controls, numeric forms, editable collections with undo, atomic action batches, calculations, and change handlers. Existing v2 apps remain compatible.

Generated apps share a [1,903-asset offline icon library](../assets/icons/README.md). Gemini selects topic-specific logos and component artwork. Tap an app's icon beside its title to search the full library and change its logo; Auto restores an inferred symbol. The picker supports touch search, physical typing, paging, and both themes. Main-screen voice input is unchanged.
