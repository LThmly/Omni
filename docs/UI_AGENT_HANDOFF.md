# Omni UI agent handoff and operating guide

This document is intended to let another coding agent begin meaningful simulator UI work without replaying the conversation. Read it before editing, then consult the actual implementation for details that may have changed. Commands below identify whether they run on the development computer or on the Pi. They assume the repository root unless stated otherwise.

Latest generated-app implementation changes are documented in [GENERATED_APPS.md](GENERATED_APPS.md): real pages, the shared layout system, numeric input, compound actions, calculations, and change handlers. Those additions supersede the earlier single-column-only component description below.

Choice-game extension: `choice_game`/`play_choice` add actual local gameplay with validated dominance rules, automatic scores, curated cached vector artwork (`firmware/game_art.py`), and an arena/reveal renderer (`firmware/choice_game.py`). `contract/fixtures/v2/rock-paper-scissors.json` is the reference. Gemini and the offline demo now generate a playable RPS game instead of random-number/manual-score widgets. The renderer blocks extra move taps for its 620 ms reveal, honors reduced motion, and persists the complete round atomically. Existing apps are not migrated automatically. See the generated-app guide and `firmware/test_choice_game.py` before extending this contract. The configured local generation model is now `gemini-3.1-pro-preview`; the local `.env` overrides the source default, so retain/check it without exposing the key.

Shared asset extension: [assets/icons/README.md](../assets/icons/README.md) documents 1,903 offline canonical assets plus aliases, the pinned Lucide source/license, lazy PNG masks, original game/sports illustrations, and rebuild instructions. `contract/asset_catalog.py` owns IDs/search/model shortlists; `firmware/icon_assets.py` owns bounded rendering caches. Optional `app.icon`, component `icon`, and item `icon` work across generated apps. `illustration` is a new fixed component. Tap a generated app's header badge to open `firmware/icon_picker.py`, search by touch/keyboard, select a persistent logo, or restore Auto. The main agent page still has no keyboard button; the picker's search keyboard is specific to this overlay. `firmware/test_icon_assets.py` checks whole-pack decoding, validation, caches, themes, picker interaction and persistence. New source/asset files must be included in any later Pi deployment; changing the schema without the catalog/pack is incomplete.

Speech preview update: empty provisional hypotheses no longer erase visible text; current-session events continue updating the preview while release drains audio. Speech/request previews now show three lines and unchanged word/scroll targets keep their existing animation timing. Agent replies now target 2–6 words and at most 48 characters. The renderer fits them to one line with word-aware ellipsis; speech previews retain three lines. An optional larger streaming Vosk model can be installed with `.venv/bin/python sim/setup_speech.py --model accurate` and selected using `--model sim/models/vosk-model-en-us-0.22-lgraph`; see [sim/README.md](../sim/README.md#microphone-setup) for measurements and the Pi 3 resource constraint. The Pi/default model remains the small model. These local source changes do not imply a device deployment or GitHub push.

## Contents

1. [Project and current snapshot](#1-what-you-are-working-on)
2. [User expectations and UI behavior](#2-user-expectations-and-product-behavior-to-preserve)
3. [Source map](#3-source-map-where-to-edit)
4. [Run the simulator](#4-fast-start-on-the-development-computer)
5. [Controls and profiles](#5-simulator-controls-and-profiles)
6. [ASR, local commands, and backend routing](#6-local-speech-local-commands-and-gemini-are-separate-layers)
7. [Gemini and the strict contract](#7-gemini-setup-and-contract)
8. [Development loop and performance](#8-a-reliable-ui-development-loop)
9. [Tests and headless screenshots](#9-tests-and-headless-screenshots)
10. [Pi connection, launch, and autostart](#10-pi-connectivity-launch-and-boot-behavior)
11. [Committed and working-tree deployment](#11-deploying-source-to-the-pi)
12. [Pi-to-simulator data/config sync](#12-sync-pi-appssettingsconfiguration-back-into-the-simulator)
13. [Troubleshooting](#13-troubleshooting-guide)
14. [Git/publication boundaries](#14-git-publication-and-local-only-files)
15. [Manual acceptance checks](#15-manual-acceptance-checklist-for-future-ui-changes)
16. [Boundaries and next-agent starter prompt](#16-known-boundaries-and-documentation-precedence)

## 1. What you are working on

Omni is a voice-and-touch device. The current physical prototype is a Raspberry Pi 3 Model B with a 5-inch 800×480 HDMI LCD and an XPT2046 touchscreen. The application renders a logical **480×800 portrait surface**, then rotates/scales it onto the physical panel. The desktop simulator uses the same logical surface upright.

The current simulator is **pygame**, not a website. Its renderer, controller, touch behavior, app data model, local command matching, speech integration, response animation, navigation, and generated components are shared with the Pi. Usually, changing `firmware/native_ui.py` changes both environments. There is no separate contemporary simulator implementation to port changes into.

The word “e-ink” appears throughout earlier history and some filenames. The current target is the Pi LCD. Earlier physical e-ink experiments used static logos, slow refreshes, dark/light experiments, and partial updates that failed. Do not revive those paths while working on the current pygame UI unless the user explicitly asks for the old hardware.

### Snapshot at handoff creation

- Development checkout: `/home/logan/Projects/SwampHacks/Omni` on an Arch Linux computer.
- GitHub: `https://github.com/LThmly/Omni`, branch `main`.
- Last pushed feature commit: `2b01f4d` — `Unify structured app contracts, local voice commands, and animated UI flows`.
- Pi SSH target: `omni@100.124.54.78` over Tailscale.
- Pi application directory: `/home/omni/Omni` (`~/Omni` when logged in as `omni`).
- **The Pi directory is not a Git repository.** `git pull` there is not the deployment method.
- The last device installation was labeled `f20118e-local-6be74190e173`, a working-tree snapshot. Its 84 source-file hashes matched the desktop before the final commit; a trailing blank-line cleanup in a cloud test was subsequently included in the commit. Do not expect its recorded deployment label to equal `2b01f4d` until a normal committed deployment is performed.
- Last complete test run: **89 firmware tests + 20 cloud tests = 109 passing**. The same suite passed on the Pi before the push.
- The simulator profile was copied from the Pi: **9 apps**, light mode, motion enabled, standard text, 20-second offline preview wait, 24-hour clock. Generated apps and preferences are mutable user data, so inspect rather than assume these remain current.
- At that sync, the nine titles were Omni, Settings, Notes, Clock, Calculator, three separate Shopping apps, and Fish Log. Repeated titles have different IDs; do not silently merge them.
- The simulator was reopened with `--backend gemini` and real Vosk speech. This is a launch argument, **not a persistent simulator backend preference**. Plain `sh sim/run.sh` defaults to the demo generation backend.
- The Pi's `.env` was copied to the ignored local `.env`. A live local Gemini request succeeded. Do not print or commit the key.
- The known working speech model is `sim/models/vosk-model-small-en-us-0.15` on both machines.
- Desktop pygame package was pygame-ce 2.5.8, with Python 3.14; Pi used system pygame 2.6.1 with Python 3.13.5. Avoid changing both package strategies incidentally.

These are observations from this session, not permanent guarantees. Recheck Git status, process state, connectivity, and profile/config files at the start of new work. Old tool-session IDs, PIDs, and `/tmp` scripts are not durable workflows.

## 2. User expectations and product behavior to preserve

The user prefers implementation and testing over a plan-only response. Work on the simulator first, then transfer changes to the actual device when requested. The user has repeatedly wanted local/device testing before publishing; the final feature batch was explicitly authorized and pushed. **That past push is not standing authorization to publish future unrelated changes.** Ask for missing facts only when necessary, and do not repeatedly ask for actions already authorized in the active task.

### Main agent page

- Large Omni symbol and wordmark. Do not add a blue circle to the logo or replace it with an unrelated icon.
- A centered block-style waveform button sits below the text area. The older “Tap to explore,” “Hold to talk,” “Listening,” and “Your request” captions were intentionally removed.
- Holding the waveform animates individual bars irregularly, rather than moving them all in a synchronized breathing wave.
- Real Vosk partial hypotheses appear live, centered beneath the wordmark. Corrections replace provisional words smoothly; finalized speech segments survive pauses.
- Releasing submits the final recognized text. The submitted request remains visible while the backend is working.
- The Omni arrows animate irregularly while waiting for the actual response. Real backend waiting is tied to response/error arrival, not a fixed ten-second animation timer.
- When waiting stops, the arrows ease to their default lengths over approximately **280 ms**. Do not abruptly snap them to rest.
- The response replaces the request and progressively reveals words with fading and small position adjustments. Keep replies centered on one line. Gemini is instructed to use 2–6 words and at most 48 characters. `short_response()` provides a measured, word-aware fallback for longer replies. Response gating checks the fitted display target so shortened acknowledgments still precede actions.
- **Show the response before performing an action.** Navigation, creation, mutation, and local setting changes wait until the complete response has actually been rendered and the text animator has settled, then hold for **1.2 seconds** before applying the action.
- Backend completion alone does not satisfy this gate. A hidden or unpainted response must not trigger navigation.
- Escape cancels an action waiting behind its acknowledgment.
- Returning to Omni clears the previous response and its animation state. Do not resurrect old response text on later visits.
- The latest request explicitly restored live transcription. Older response-only comments, tests, or screenshots are historical, not the desired behavior.

### App selector and app pages

- Built-in apps: **Omni, Settings, Notes, Clock, Calculator**, in that order. Do not restore Ping Pong or unrelated old default demos.
- The circular wheel extends off the screen. The selected node grows/inverts; neighboring icons remain visible on the arc.
- The selector has no bottom-center hold-to-talk button.
- Drag around the wheel, use a mouse wheel, or use Up/Down to rotate. Tap a neighbor to select it; tap the focused app to open it.
- Main page ↔ selector uses a roughly **480 ms** eased brand/wheel transition.
- Selector ↔ app uses a roughly **360 ms** eased horizontal slide in opposite directions for opening/returning. Incoming/outgoing page surfaces are cached once per transition to avoid repainting both pages every frame.
- For voice navigation to an app, first show the selector at the app **farthest around the registry from the target**, rotate to the desired app, hold focus for about **120 ms**, then open it with the selector-to-app transition.
- This farthest-start behavior intentionally replaced the earlier shortest-animation approach. Once positioned at the farthest app, the wheel still uses a bounded shortest route to the target.
- Reduced motion skips the visual animations, including wheel/slide movement, but retains response-before-action ordering and its reading pause.
- Built-in Notes supports touch/physical-keyboard editing; Clock supports 12/24-hour time; Calculator supports touch/keyboard arithmetic.
- Settings includes Delete generated apps. It opens a separate Cancel/Delete confirmation, removes generated apps and their saved data, and retains the five defaults, Notes content, and preferences. It stays in Settings afterward and clears deleted-app timer/game/page caches. The row is disabled when no generated apps exist. Escape/Back cancels; this is separate from Ctrl+D, which also clears Notes.

### Touch handling

A previous bug treated ordinary finger drift as scrolling, causing back buttons, settings, calculator keys, and app controls to appear unresponsive. A second bug compared only action names on release, allowing adjacent keys with the same action type to activate the wrong value.

Current behavior deliberately distinguishes gestures:

- `TOUCH_SLOP = 14` logical pixels distinguishes a tap from a wheel/content drag.
- `TOUCH_PADDING = 12` expands the release/cancellation tolerance around fixed controls.
- Fixed controls own their gesture. Finger drift inside their padded bounds is tolerated; leaving those bounds cancels the tap.
- Scrollable Notes/component content can become a scroll gesture once movement crosses the threshold. Scrolling must not toggle items or execute buttons on release.
- Wheel dragging has its own angular path and snaps to an integer selection on release.
- Hits are rebuilt every paint. Compare complete control identity, including rectangle and payload, then activate the originally pressed control. Never activate a neighbor just because both hits have `act='key'` or `act='calc'`.
- Touch-generated mouse events are filtered in the shared event loop so one finger is not also interpreted as a second mouse click.
- Test real down/move/up sequences across intervening paints, not just direct calls to `activate()`.

## 3. Source map: where to edit

| File | Responsibility |
| --- | --- |
| `sim/run.sh` | Desktop launcher; selects project `.venv` if available. |
| `sim/run.py` | Adds `firmware/` to the import path and invokes the real phone entry point with `--sim`. No separate renderer. |
| `firmware/native_ui.py` | Primary current renderer/controller. `NativeScreen` draws screens; `NativeApp` coordinates input, speech, replies, preferences, navigation, deferred effects. Start here for most UI work. |
| `firmware/phone.py` | Shared base classes, fonts/text helpers, hit records, app rendering, coordinate mapping, process lock, pygame event loop, CLI. `main()` creates `NativeApp`; older base rendering methods coexist and are not all active. |
| `firmware/components.py` | Device-owned rendering of fixed generated-app components. |
| `firmware/transcript.py` | `TranscriptAnimator`: word wrapping, stable prefixes/suffixes, corrections, fade/movement, scrolling, and `settled()`. |
| `firmware/speech.py` | Vosk model/capture worker, partial/segment/final events, cancellation, native-rate audio, queue handling. |
| `firmware/local_commands.py` | Explicit offline command matching, spoken arithmetic, preferences, notes, time/date, existing generated-app actions. No network. |
| `firmware/logic.py` | Registry/state persistence, app lookup, built-in/generated app logic, `last_turn`, atomic app mutation integration. |
| `contract/runtime.py` | Canonical JSON/semantic validation, atomic approved operations, navigation helpers and phrase normalization. |
| `contract/build_schema.py` | Single source generating the app, turn, wrapped strict, and model-facing schemas. |
| `contract/legacy.py` | One-way migration of old generated templates into composed apps. |
| `contract/fixtures/v2/` | Validated examples, including a real Gemini-generated counter and follow-up turns. |
| `cloud/try_turn.py` | Gemini client, system instructions, model schema, response parsing, transport/error handling. |
| `cloud/stub_server.py` | Optional HTTP turn endpoint and preview integration. |
| `firmware/demo.sh` | Pi first-time panel/autostart setup followed by launch. May install packages or reboot during bring-up. |
| `firmware/start-demo.sh` | Normal Pi launcher; selects venv/backend/microphone, runs phone, reopens closed windows when appropriate. |
| `firmware/deploy.py` | Commit-based SCP deployment, source hashes/backups, Pi dependency install/tests, restart. |
| `firmware/shell.py` | Thin compatibility entry point into `phone.main()`. |
| `sim/setup_speech.py` | Downloads/validates the small English Vosk model. |
| `sim/VOICE_COMMANDS.md` | User-facing catalog of supported local phrases and deliberate fallbacks. |

Important methods in `native_ui.py`:

- `NativeScreen.paint()` wraps `_paint()` and manages cached page slides.
- `transition_progress()` handles the home/arc morph; `wheel_to()` and `update_wheel()` handle wheel easing. Wheel duration grows with travel from a 280 ms base and caps at 650 ms. Current geometry is `CX=-8`, `CY=686`, `RADIUS=328`, `STEP=22°`, `FOCUS=-42°`; these are logical portrait coordinates.
- `palette()` updates monochrome colors and cached logo marks when theme changes.
- `logo_offsets()` handles waiting motion and settling.
- `response_visual()` chooses speech/request/response text and reveals response words at approximately **42 ms per word** before passing them into `TranscriptAnimator`.
- `NativeApp.send()` clears stale context, checks local commands first, and only starts a backend worker when no local command matches.
- `poll()` receives/validates turns and presents their response.
- `poll_response()` waits for rendered/settled text plus the reading pause.
- `apply_result()` applies a canonical turn; `apply_local_effect()` performs trusted preferences/Notes/calculator effects.
- `navigate_app()` positions the farthest wheel start; `poll_navigation()` advances arrive → rotate → focus → open.
- `set_launcher()` controls return behavior and clears stale response text when entering Omni, except during submission when the live transcript should remain.
- `on_down()`, `on_move()`, `on_up()` and `activate()` are the touch path.
- `poll_speech()` bridges worker events into the controller; `apply_speech_result()` maintains partial/finalized segments.
- `frame()` updates timing/preview speech and delegates to the base display frame.

The wordmark font is `sim/neuropolitical.ttf`. Preserve the existing logo geometry and font cache unless a requested design change requires touching them.

## 4. Fast start on the development computer

### Existing configured checkout

```sh
cd /home/logan/Projects/SwampHacks/Omni
sh sim/run.sh --stop
sh sim/run.sh --backend gemini
```

The stop command targets the simulator's own lock/profile. Reopening is necessary after code changes: the running Python process does not hot-reload source.

For no-network UI iteration with real microphone recognition:

```sh
sh sim/run.sh --backend demo
```

For scripted speech/UI iteration without loading Vosk:

```sh
sh sim/run.sh --speech demo --backend demo
```

The scripted preview is intentionally explicit. Do not present it as functioning ASR. Its legacy hold path can still try the fallback `AudioRecorder`; it is not a guarantee that no audio device will be touched. For strictly audio-free interaction, type commands without holding the waveform or use the mocked headless/test workflow below. Use real Vosk when testing partial transcription, silence, microphone errors, capture cancellation, or final-result submission.

For a disposable profile:

```sh
sh sim/run.sh --backend demo --speech demo --store /tmp/omni-ui-scratch/registry.json
```

`NativeApp` creates the profile directory through its persistence path. A custom `--store` moves preferences and the simulator lock alongside that registry. Stop that custom instance with the same `--store`:

```sh
sh sim/run.sh --store /tmp/omni-ui-scratch/registry.json --stop
```

Avoid an accidental data reset: Ctrl+D deletes generated apps and Notes content in the active profile. Use a scratch profile for destructive testing.

### Fresh desktop environment

```sh
cd /path/to/Omni
python3 -m venv .venv
.venv/bin/pip install -r sim/requirements.txt
.venv/bin/python sim/setup_speech.py
sh sim/run.sh --backend gemini
```

Requirements currently pin pygame-ce 2.5.8, Vosk 0.3.45, sounddevice 0.5.6, and include the shared JSON Schema dependency. PortAudio is a system dependency (`portaudio` on Arch, `libportaudio2` on Debian/Pi). Follow the host's package-installation/approval requirements; do not replace a working environment merely to match a version string.

The downloader exits successfully without redownloading when `am/final.mdl` already exists. Model files are ignored, not supplied by Git. A new checkout therefore needs model setup even when all source files are current.

### Useful launch variants

```sh
sh sim/run.sh --help
sh sim/run.sh --list-audio-devices
sh sim/run.sh --backend gemini --audio-device pipewire
sh sim/run.sh --backend gemini --audio-device 6
sh sim/run.sh --backend gemini --model /path/to/unpacked-vosk-model
```

The names/indexes above are examples; list the actual desktop inputs first. Do not copy the Pi-specific Voice HAT name onto the desktop. Stable device names are preferable to numeric indexes when available.

## 5. Simulator controls and profiles

| Interaction | Result |
| --- | --- |
| Tap main logo area | Open app wheel. |
| Tap small Omni mark on selector | Return to main agent page; clear old response. |
| Drag the wheel / mouse wheel / Up or Down | Rotate app selection. |
| Tap neighboring app | Rotate it into focus. |
| Tap selected app / Enter when appropriate | Open it. |
| Hold waveform ≥350 ms, then release | Capture/submit speech. |
| Release a short hold / Escape / lose focus | Cancel capture; do not invent a default request. |
| Type on main page, then Enter | Send a typed request; useful for isolating ASR from routing/UI bugs. |
| Main agent input | Hold the waveform to speak, or type using a physical keyboard. There is no on-screen keyboard button on this page. |
| Back button / Escape inside app | Return to selector. |
| Escape on selector | Return to Omni. |
| Escape during pending acknowledgment | Cancel queued action. |
| Escape during automatic wheel navigation | Cancel route at selector. |
| Ctrl+Shift+Q | Quit. |
| Ctrl+D | Reset active profile to five defaults; destructive to generated apps and notes. |

Default data locations:

| Item | Development simulator | Pi |
| --- | --- | --- |
| Registry | `~/.omni/simulator/registry.json` | `~/.omni/pi-ui/registry.json` |
| Preferences | `~/.omni/simulator/preferences.json` | `~/.omni/pi-ui/preferences.json` |
| Process lock/PID | `~/.omni/simulator/shell.pid` | `~/.omni/shell.pid` |
| Legacy registry | Preserve if present | Preserve `~/.omni/registry.json` |
| Migration backup | `registry.pre-components.json` next to profile | Same convention |
| Deployment manifest | Not the simulator profile | `~/Omni/.omni-deployed.json` |
| Deployment log | Launcher output in terminal | `~/.omni/ui-deploy.log` |
| Source backups | Normal Git/local workflow | `~/.omni/deploy-backups/` |

Profile schema includes registry/state and persisted `last_turn`. Preferences contain `theme`, `motion`, `text_scale`, `wait_seconds`, and `clock24`. Allowed values are validated when opening the profile. Source sync does **not** automatically synchronize these machine-local files.

A profile backup from the last Pi-to-simulator copy was stored under `~/.omni/simulator/sync-backups/20261017-185957/`. Treat that path as historical; list actual backups before restoring.

## 6. Local speech, local commands, and Gemini are separate layers

### Speech lifecycle

Vosk runs locally. The model is loaded once; capture and decoding occur on a worker thread so pygame stays responsive. Audio uses mono 16-bit PCM at the input's native rate; Vosk resamples internally. The worker emits ready/warning/partial/segment/final/error events tagged by session ID.

The UI displays live partials but **does not execute local commands from provisional speech**. On release, capture drains, all finalized segments are combined, and only the final text is sent through `NativeApp.send()`. Late or cancelled-session events must not create a request.

Brief PortAudio overruns are warnings. A full decoder queue is an error, rather than silently submitting truncated audio. Audio is not retained on disk by the Vosk path. The old `AudioRecorder`/recorded-WAV fallback still exists in the base module; do not confuse it with the normal Vosk path.

An earlier experiment deferred recognition until after release and added audio processing. The user found it equally inaccurate and slower and requested a revert. Do not reintroduce deferred ASR/audio-leveling latency as an unsolicited “accuracy improvement.”

### Local command matching

`match_command(text, prefs, registry)` in `firmware/local_commands.py` returns a `LocalCommand` with a canonical contract turn and optionally a trusted device-owned effect. It does not call the model. Matching is explicit and complete, with polite-prefix normalization and many navigation aliases.

Supported groups include:

- Navigation to built-ins, selector/home, or a uniquely named existing generated app.
- Light/dark/day/night mode and theme toggles.
- Motion/reduced motion, text size, clock format, and offline preview delay.
- Device-local time/date questions.
- Append/read built-in Notes content.
- Spoken arithmetic using digits or English numbers, including decimals, hundreds/thousands, negatives, and parentheses when typed.
- Existing generated-app buttons by declared label and app name.
- Appending content to a uniquely matched generated list through its existing append action.

See [the full phrase catalog](../sim/VOICE_COMMANDS.md). The tests exercise a 228-case navigation phrase matrix in addition to task-specific cases.

Questions about using a feature, negations, unknown pages/tasks, duplicate app names, undeclared actions, and combined instructions fall through to Gemini. Do not broaden matching into substring/fuzzy guesses that accidentally interpret a question or part of a dictated note as an action. Never execute note/list content as a second command.

Generated app mutations use only approved operations and are validated atomically before changing state. List length/item-size errors produce clear local responses rather than a fabricated success.

### Backend choices

| Argument | Actual meaning |
| --- | --- |
| `--backend demo` | Local template generation; unknown general questions receive an explicitly labeled offline response. No model/server needed. |
| `--backend gemini` | Direct call to `cloud.try_turn.ask()` for requests not handled locally. |
| `--backend stub` | HTTP POST to the configured endpoint; default `http://127.0.0.1:8787/v1/turn`. |
| `--live` | Compatibility choice for the HTTP stub backend, **not** direct Gemini. |
| `--speech vosk` | Real local speech recognition; independent of generation backend. |
| `--speech demo` | Scripted partial-result preview/legacy recorded-audio path; independent of backend. |

The preview delay is only for **offline demo app generation**. Real Gemini/stub calls wait for their actual result, not that preference. Local commands bypass the backend and its preview delay, while retaining the user-requested response animation and reading pause.

The HTTP “stub” is not guaranteed offline when `.env` has a real key: its `respond()` loads environment configuration and can forward to Gemini. Use `--backend demo` for reliably no-network UI work.

## 7. Gemini setup and contract

Both machines load `.env` from the **repository root**, not the profile or current shell's home directory. The key is read from `GEMINI_API_KEY` or `GOOGLE_API_KEY`; `GEMINI_MODEL` optionally overrides the code's default. Existing environment variables take precedence because `load_env()` uses `setdefault()`.

The current client uses the Vertex express `aiplatform.googleapis.com` endpoint. The configured key was bound/restricted to that service; swapping it to the similarly named generative-language endpoint broke that setup. Inspect `cloud/try_turn.py` before changing provider configuration. The default model at handoff is `gemini-3.8-flash`; this is a code/config observation, not a promise about future provider availability.

The copied local `.env` has mode 0600 and is Git-ignored. Do not put credentials in documentation, example commands, logs, shell tracing, screenshots, or commits. To copy the device configuration again, from the **development computer**:

```sh
cd /home/logan/Projects/SwampHacks/Omni
# Back up an existing local .env privately before replacement if needed.
umask 077
scp omni@100.124.54.78:~/Omni/.env .env
chmod 600 .env
```

Use the configured SSH credentials or credentials supplied in the active conversation. This document intentionally does not embed a login password or API key. The user has authorized using the device's key for the local simulator; do not ask them to retype it unnecessarily when the configured file is available.

One small live connectivity check (makes a real API request):

```sh
.venv/bin/python -c 'from cloud.try_turn import ask; r=ask("Say hello briefly.", []); print(r["intent"], r["op"])'
```

Do not add keys to the command line or print environment contents. A successful check prints `message say`. Actual phrasing may vary; the response must pass validation.

### Canonical v2 contract

The model returns a wrapped object `{"turn": {...}}`; `ask()` returns the validated **inner** turn. Turns include `schema_version: 2`, `intent`, `op`, and plain user-facing `say`.

| Intent | Typical operation | Meaning |
| --- | --- | --- |
| `message` | `say` | Answer/greeting/general message. |
| `create_app` | `propose` | Full new app composed from predefined components. |
| `update_app` | `mutate` | Approved operations on an existing app ID. |
| `navigate` | `navigate` | Open a named page or existing generated app. |

A clarification/decline can use `op='say'` while retaining the original classified intent. `last_turn` persists the validated classification. Device-local preference/Notes/calculator effects are trusted local effects accompanying canonical message turns; they are not new model operations and must not be smuggled into unvalidated model JSON.

Named navigation destinations are `agent`, `apps`, `settings`, `notes`, `clock`, `calculator`, and `app`. Named destinations use `app_id=null`; destination `app` requires an existing generated app ID.

New generated apps use `module='composed'`, with `id`, `title`, `state.fields`, `components`, and `actions`. Fields are typed text, bounded numbers, booleans, or items. Components are device-owned text/number/progress/toggle/list/input/button elements. Actions are approved set/increment/toggle/append/clear/remove_checked operations. Bindings, IDs, button actions, and source/target types must all resolve.

No arbitrary code, URLs, custom widget implementation, or layout coordinates are generated. The device owns layout and interaction. Old checklist/scoreboard/progress/key-value generated apps migrate one-way into composed apps, with a registry backup.

Schemas are generated from `contract/build_schema.py`:

```sh
.venv/bin/python contract/build_schema.py
.venv/bin/python contract/build_schema.py --check
```

`turn.gemini.json` is a structural provider-compatible projection. The fully bounded union initially produced HTTP 400 when sent directly as the model schema. Full limits and semantic checks still run locally against the strict schema and runtime graph before application. Do not “fix” the provider workaround by weakening local validation or by hand-editing generated schemas.

The client requires a completed STOP response, combines visible text parts while excluding thought parts, rejects malformed/duplicate-key JSON and invalid references, and raises `TurnError` on failures. Model failures must not silently become fake successful demo apps.

## 8. A reliable UI development loop

1. Read `AGENTS.md`, this guide, and current Git status. Inspect any existing user changes; do not overwrite them.
2. Identify the active renderer/controller path rather than editing an older base implementation that is no longer used.
3. Reproduce the issue in the simulator. Use typed commands to separate UI/routing from recognition quality. Use a scratch profile when resetting or changing test data.
4. Implement the smallest coherent shared change. Preserve the established text/response/action ordering and touch capture semantics.
5. Run the relevant focused tests. Add a regression test for gesture/state bugs; avoid tests that only repeat trivial drawing implementation.
6. Restart the simulator and manually exercise the real interaction, including transitions, repeated visits, dark/light modes, and reduced motion when relevant.
7. Run the full appropriate checks before deployment/publication.
8. Deploy to Pi when requested and verify the UI actually restarted with the expected backend/microphone.
9. Push only when requested. A local commit can be deployed without being pushed.
10. Report what changed, checks performed, and whether it is local-only, deployed, committed, or pushed. Do not conflate these states.

### Performance principles for Pi 3

- Keep capture, recognition, HTTP/model requests, and file-transfer work off the pygame event/render thread.
- Use elapsed-time-based easing, not frame-count assumptions or sleeps in event handlers. The shared loop currently caps at 60 FPS with `clock.tick(60)`; that is a target cap, not measured Pi throughput.
- Reuse fonts, assets, and cached transition surfaces. Do not rerender two complete app pages on every slide frame.
- Respect `screen.busy` and existing gesture capture, but do not leave the UI permanently locked after a transition or cancellation.
- Validate and deep-copy before mutating live app state; avoid unnecessary registry-wide work per frame.
- Maintain reduced-motion behavior and reliable cleanup for cancelled speech, actions, and navigation.
- Test on the physical panel before claiming performance improvements; desktop smoothness alone is not Pi evidence.

## 9. Tests and headless screenshots

Run from the repository root on the **development computer**:

```sh
.venv/bin/python -m unittest discover -s firmware -p 'test_*.py'
.venv/bin/python -m unittest discover -s cloud -p 'test_*.py'
.venv/bin/python contract/build_schema.py --check
git diff --check
```

Focused suites:

```sh
.venv/bin/python -m unittest discover -s firmware -p 'test_native_ui.py'
.venv/bin/python -m unittest discover -s firmware -p 'test_local_commands.py'
.venv/bin/python -m unittest discover -s firmware -p 'test_transcript.py'
.venv/bin/python -m unittest discover -s firmware -p 'test_speech.py'
.venv/bin/python -m unittest discover -s cloud -p 'test_contract.py'
.venv/bin/python -m unittest discover -s cloud -p 'test_turn.py'
```

The UI tests configure dummy SDL drivers, use temporary profiles, and mock the fallback recorder. A previous test accidentally opened `arecord`, occupied the physical mic, and caused subsequent microphone failures. Preserve recorder mocking and `app.close()` cleanup; do not run hardware capture in ordinary unit tests.

Fake-time tests must advance actual paint frames. New responses reveal words progressively, then fade/reflow, then wait to become readable. Calling `poll()` once after a reply is no longer expected to immediately create/open an app. `finish_response()` and `settle_navigation()` in the UI tests illustrate the correct sequence.

For a headless layout screenshot without touching real profiles or microphone devices:

```python
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'firmware')
import pygame
from native_ui import NativeApp

pygame.init()
with tempfile.TemporaryDirectory() as temporary, patch('native_ui.legacy.AudioRecorder'):
    app = NativeApp('http://unused', 'none', False,
                    Path(temporary) / 'registry.json', backend='demo')
    try:
        app.screen.paint(app.phone, app.device, 1000, '')
        app.device.say = 'A sample response for layout review.'
        for ticks in range(1033, 2300, 33):
            app.screen.paint(app.phone, app.device, ticks, '')
        pygame.image.save(app.phone, '/tmp/omni-ui-review.png')
    finally:
        app.close()
pygame.quit()
```

To inspect a transient animation, save frames at known intermediate timestamps rather than only the final state. For end-to-end interactions, use the test helpers or call down/move/up and `poll()` with the same frame ordering as the real loop. A dummy-driver screenshot proves layout, not desktop/window/input or physical-panel behavior.

## 10. Pi connectivity, launch, and boot behavior

All transfers/deployment commands originate on the **development computer**. Commands under an SSH prompt run on the **Pi**. Do not accidentally install Pi packages on the desktop or run `scp` from the wrong side.

### Connect from the development computer

```sh
ssh omni@100.124.54.78
```

If the address stops working:

```sh
tailscale status
tailscale ping --timeout=5s --c=2 100.124.54.78
ssh -o ConnectTimeout=10 omni@100.124.54.78
```

The old LAN address `10.136.108.116` was incorrect/stale and produced “No route to host.” Tailscale is the established route. In this session SSH briefly timed out even while the peer later answered Tailscale pings; reconnecting worked. Do not infer permanently missing permissions from one transient timeout. Confirm the Pi is powered/networked and ask for a new address only when needed.

The user has previously used password authentication. Use an interactive TTY for SSH/SCP when necessary; do not place passwords in a command, source file, `sshpass` argument, or the repository. Do not reuse historical process/session IDs as if they were current.

### Launch on the Pi

After SSH login:

```sh
cd ~/Omni
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WAYLAND_DISPLAY=wayland-0
export SDL_VIDEODRIVER=wayland
sh firmware/start-demo.sh
```

For first-time panel/autostart bring-up, use:

```sh
cd ~/Omni
sh firmware/demo.sh
```

`demo.sh` checks Pi hardware, may install system packages, writes desktop/labwc autostart entries, invokes panel configuration, and may reboot if setup changed. `start-demo.sh` is enough for routine launches of an already configured panel and avoids repeating bring-up work.

The Pi must have an active graphical login. Exporting Wayland variables from SSH points at that session; it does not create a compositor or log in a user. If `wayland-0` is not the actual display socket, inspect `/run/user/$(id -u)/wayland-*` in the live session and use the real value.

Running `python3 firmware/shell.py` from `/home/omni` fails because `firmware/` is under `~/Omni`. Change directory or use an absolute path. The source entry points are interchangeable for the modern UI, but `--sim` selects the simulator profile and should not be accidentally passed on the device.

### Persistent Pi runtime choices

These files are read by `start-demo.sh`:

```sh
mkdir -p ~/.omni
printf 'gemini\n' > ~/.omni/app-backend
printf 'vosk\n' > ~/.omni/speech-mode
printf 'snd_rpi_googlevoicehat\n' > ~/.omni/audio-device
```

Only write the last value when the Pi actually uses that Voice HAT. The stable name was verified on this prototype; another board/microphone can require a different setting.

The launcher selects `.venv/bin/python` when available. Without `speech-mode`, it selects Vosk when the model exists, otherwise demo speech. The generation backend defaults to demo unless configured or overridden.

Normal launch arguments can override backend/speech choices, but inspect `start-demo.sh` when changing its behavior: the optional auto-start of the HTTP stub checks the saved backend variable before the appended CLI overrides. For deterministic stub troubleshooting, start the server explicitly.

### Stop and inspect on the Pi

```sh
cd ~/Omni
.venv/bin/python firmware/phone.py --stop
tail -n 60 ~/.omni/ui-deploy.log
pgrep -af 'firmware/phone.py|start-demo.sh|arecord'
```

The deployed launcher writes unbuffered application output to `ui-deploy.log`. A normal terminal launch writes to that terminal instead. Look for the source path, `App backend: gemini`, model-loading line, microphone ready/warning/error lines, and recognized requests.

Window close and graceful quit are different: exit code 2 causes `start-demo.sh` to reopen the UI; Ctrl+Shift+Q or `--stop` leaves it stopped. The deployer explicitly stops the launcher parent before replacing the UI so a previous loop cannot race the new launch.

### Does it open automatically when plugged in?

`demo.sh` installs desktop and labwc login autostart entries. Therefore it can open automatically **when the graphical session logs in**. It is not proof that every cold boot/power connection reaches that session; automatic login and the compositor must also be configured. Do not promise a headless boot service or unconditional power-on launch without checking the actual device configuration. There is no need to change boot/panel setup for a normal UI edit.

## 11. Deploying source to the Pi

### Preferred: deploy a local Git commit

A push is **not** necessary for deployment. From the **development computer**, after tests and an appropriately scoped local commit:

```sh
cd /home/logan/Projects/SwampHacks/Omni
python3 firmware/deploy.py omni@100.124.54.78 --backend gemini
python3 firmware/deploy.py omni@100.124.54.78 --verify
```

The deployer has no model/pygame dependency on the local system Python, so `python3` is sufficient there. The application/tests on the Pi use its selected virtual environment.

The current deployer:

1. Requires clean **tracked** files relative to `HEAD`.
2. Archives that commit with `git archive`; staged/untracked new code is not included until committed.
3. Adds `.omni-deployed.json` containing the commit and managed-file SHA-256 hashes.
4. SCPs the archive and invokes a remote Python helper. The Pi itself does not need `.git`.
5. Stops the old launcher/UI, then backs up overwritten source under `~/.omni/deploy-backups/`.
6. Extracts/validates source and removes a small explicit set of retired browser files.
7. Preserves `.env`, the virtual environment, downloaded speech models, microphone/backend config, and machine profiles.
8. Installs `cloud/requirements.txt` into the Pi venv; it does not reinstall all desktop pygame requirements.
9. Runs both firmware and cloud suites on the Pi with dummy SDL drivers.
10. On an extraction/dependency/test failure, restores previous managed source and relaunches it.
11. Saves the requested backend, restarts the UI using Wayland, and waits for the backend startup log.
12. Reports deployment success. `--verify` compares current files to the commit without restarting the UI.

Rollback is strongest around extraction/install/tests. A failure after launch/startup is reported, but is not the same automatic rollback path. Inspect the log and restore/relaunch deliberately rather than assuming every failure rolled back. Backups contain source files, not a complete operating-system/venv/profile snapshot. Pip changes are not rolled back with source.

`--verify` compares against the current committed tree and requires matching deployment metadata. It will not label an older working-tree snapshot as this GitHub commit just because most files happen to match. After committing/pushing a formerly uncommitted deployment, run a normal deploy to align manifest labels if that alignment is needed; do not falsify `.omni-deployed.json`.

### Test without committing: explicit working-tree snapshot

Use this only when the user wants to test uncommitted source on the Pi. The public deployer intentionally rejects that state. The previous session used temporary snapshot scripts with honest `-local-<digest>` labels. Do not quietly modify the clean-commit requirement or claim such a snapshot is on GitHub.

The following self-contained recipe reuses the same remote backup/test/restart helper. Save it as `/tmp/omni-deploy-working-tree.py` and run it from the **development repository root**. Review its file list first. It includes existing tracked files and only the explicitly listed new files; add any new UI dependencies to `extra_files`. Do not add `.env`, profile data, models, `.pio`, or the old preview archive.

```python
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import tempfile

root = Path.cwd()
target = 'omni@100.124.54.78'
extra_files = []  # Example: ['firmware/new_widget.py']; explicit, reviewed paths only.
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root)
names = {item.decode() for item in tracked.split(b'\0') if item}
names.update(extra_files)
for name in names:
    path = (root / name).resolve()
    forbidden = name.startswith(('.venv/', 'sim/models/', 'firmware/.pio/', 'eink-preview/'))
    private = Path(name).name == '.env' or (Path(name).name.startswith('.env.') and Path(name).name != '.env.example')
    if not path.is_relative_to(root.resolve()) or forbidden or private or name == '.omni-deployed.json':
        raise SystemExit('Unsafe snapshot path: ' + name)
missing = [name for name in names if not (root / name).is_file()]
if missing:
    raise SystemExit('Handle deleted/missing tracked files explicitly: ' + ', '.join(missing))
print('Review snapshot files:')
for name in sorted(names):
    print(name)
files = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
         for name in sorted(names)}
snapshot = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
label = base[:7] + '-local-' + snapshot[:12]
manifest = dict(commit=label, base_commit=base, working_tree=True,
                snapshot=snapshot, files=files)
spec = importlib.util.spec_from_file_location('omni_deploy', root / 'firmware/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
with tempfile.TemporaryDirectory(prefix='omni-preview-deploy-') as temporary:
    archive = Path(temporary) / 'source.tar'
    with tarfile.open(archive, 'w') as output:
        for name in sorted(names):
            output.add(root / name, arcname=name, recursive=False)
        body = json.dumps(manifest, indent=2).encode()
        entry = tarfile.TarInfo('.omni-deployed.json')
        entry.size = len(body)
        output.addfile(entry, io.BytesIO(body))
    remote = '/tmp/omni-preview-' + snapshot[:12] + '.tar'
    subprocess.run(['scp', str(archive), target + ':' + remote], check=True)
    command = shlex.join(['python3', '-', remote, 'Omni', label, 'no', 'gemini'])
    subprocess.run(['ssh', target, command], input=deploy.REMOTE,
                   text=True, check=True)
print('Installed local snapshot:', label)
```

Run the saved script:

```sh
python3 /tmp/omni-deploy-working-tree.py
```

The file-list output is for review, not an authorization substitute: run the deployment only within the user's requested testing scope. This recipe does not safely model arbitrary source deletions; handle those explicitly or make a committed release. The remote helper also does not delete every unmanaged old source file. Source verification describes the managed set, not every file under `~/Omni`.

### Why one-file SCP often appeared to do nothing

SCP overwrites a file on disk but does not replace already imported classes in the running Python process. The Pi may still show the old renderer until the UI is restarted. Also, UI work can span `native_ui.py`, `phone.py`, `components.py`, `transcript.py`, `local_commands.py`, and the contract. Copying only `phone.py` is often incomplete.

For a deliberately tiny standalone change, manual SCP can be useful, but restart the actual UI and verify its source path. Prefer the tested archive deployer for the shared feature set. Never run `git pull` in `~/Omni` as a substitute.

### Fresh/rebuilt Pi dependencies

Only if the existing setup is missing; do not repeat system bring-up on every UI iteration:

```sh
cd ~/Omni
sudo apt install python3-pygame python3-venv libportaudio2 alsa-utils
python3 -m venv --system-site-packages .venv
.venv/bin/pip install vosk==0.3.45 sounddevice==0.5.6
.venv/bin/pip install -r cloud/requirements.txt
.venv/bin/python sim/setup_speech.py
```

Then configure `.env`, `~/.omni/app-backend`, speech mode, and the actual microphone as described above. The system-site-packages venv intentionally reuses the Pi's apt pygame. Avoid installing the desktop pygame-ce pin over a working Pi package just to make package lists identical.

### Inspecting/restoring a source backup

On the **Pi**, identify a specific backup and inspect its contents first:

```sh
ls -lt ~/.omni/deploy-backups/
tar -tzf /home/omni/.omni/deploy-backups/CHOSEN_BACKUP.tar.gz
```

If restoring is the authorized recovery action, stop the UI, extract the chosen backup into `~/Omni`, then launch from the graphical session. Do not paste the placeholder path literally or overwrite `.env`/profiles from an unrelated archive. A source backup can predate newly added files and does not clean every new file automatically; use its manifest and the deployment failure context when restoring.

## 12. Sync Pi apps/settings/configuration back into the simulator

Because source is shared, “sync the sim” often means two different things:

1. Restart the desktop process after editing/deploying the same source.
2. Copy device-local registry/preferences/configuration if the user wants the same apps and settings.

The normal source deployer preserves profiles; it does not copy device data back. A Git pull does not transfer `.env`, models, notes, or generated apps.

For profile-only sync, stop the simulator first. From the **development computer**:

```sh
cd /home/logan/Projects/SwampHacks/Omni
sh sim/run.sh --stop
sync_dir=$(mktemp -d /tmp/omni-profile-sync.XXXXXX)
scp omni@100.124.54.78:~/.omni/pi-ui/registry.json "$sync_dir/registry.json"
scp omni@100.124.54.78:~/.omni/pi-ui/preferences.json "$sync_dir/preferences.json"
sim_profile="$HOME/.omni/simulator"
sim_backup="$sim_profile/sync-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$sim_backup"
if [ -f "$sim_profile/registry.json" ]; then
    cp "$sim_profile/registry.json" "$sim_backup/registry.json"
fi
if [ -f "$sim_profile/preferences.json" ]; then
    cp "$sim_profile/preferences.json" "$sim_backup/preferences.json"
fi
python3 -m json.tool "$sync_dir/registry.json" >/dev/null
python3 -m json.tool "$sync_dir/preferences.json" >/dev/null
cp "$sync_dir/registry.json" "$sim_profile/registry.json"
cp "$sync_dir/preferences.json" "$sim_profile/preferences.json"
sh sim/run.sh --backend gemini
```

Run this while device editing is idle if a consistent point-in-time profile is important. Registry/preferences are separate files. The UI saves them atomically individually, but copying one and then the other is not a transaction across both.

For Gemini configuration, use the private `.env` SCP workflow in section 7, preserving a previous local configuration if present. Do **not** copy the Pi's `snd_rpi_googlevoicehat` input selection to the desktop. Select an actual local microphone instead. Do not copy the running process's PID/lock file.

For source verification, read `~/Omni/.omni-deployed.json` over SSH, compare its managed hashes with device files, and compare those with the local working tree. If device source changed independently, bring the actual changed files back with a backup before merging them. Do not overwrite newer local work merely because an older device snapshot exists.

The last full sync verified 84 managed files, copied nine apps/preferences, privately copied `.env`, backed up the old simulator profile, and relaunched with Vosk/Gemini. The simulator and Pi then had the same UI code and starting app data, while remaining independent profiles afterward.

## 13. Troubleshooting guide

| Symptom | Likely cause and next check |
| --- | --- |
| Screen still shows old UI after SCP | Existing Python process has not restarted, wrong file copied, or wrong path. Verify launch log/source path and deploy/restart the complete managed set. |
| `fatal: not a git repository` on Pi | Expected: it is an SCP directory. Deploy from the development checkout. |
| Cannot find `/home/omni/firmware/shell.py` | Wrong working directory. Use `cd ~/Omni` or absolute paths. |
| “Omni is already running” | Single-instance lock. Use the simulator stop command for the simulator profile; Pi stop command for Pi. Check the actual host process rather than launching duplicates. |
| Simulator looks unchanged after code edit | No hot reload. Stop and restart it. |
| Sim responds with offline-preview text | Plain `sh sim/run.sh` used demo backend. Relaunch `--backend gemini`; `--live` means stub, not direct Gemini. |
| Missing-key error despite `.env` elsewhere | Only repository-root `.env` is loaded. Check presence/key-variable name without printing values. An exported old key can take precedence over the file. |
| Gemini HTTP 400 after schema change | Check structural `turn.gemini.json` projection and provider constraints. Keep full local strict/semantic validation. |
| Fake successful app after network error | Regression: failures should surface as `TurnError`/visible failure, never silent template fallback. |
| No window from SSH | Pi lacks active graphical login or correct Wayland/runtime environment. Exporting variables does not create a desktop. |
| `No route to host` / timeout | Check Tailscale/actual IP and SSH connectivity. Old LAN IP is stale. |
| Host SSH config “Bad owner or permissions” from an agent sandbox | In this environment, SSH/SCP sometimes needed normal host/escalated execution. Use the environment's approval mechanism rather than changing global SSH config or bypassing checks. |
| Microphone error immediately on hold | List actual inputs, use stable name, check PortAudio/model/dependencies and device contention. `arecord` from an old test/process can occupy the Pi mic. Inspect processes before changing ASR architecture. |
| Speech visible but no response | Distinguish ASR finalization, local match, backend request, and response gate. Inspect recognized text/logs. A response must finish drawing before actions occur. |
| Speech never appears | Confirm real Vosk mode, actual partial events, active session ID, and `response_visual()` text mode. Do not replace real input with a scripted preview to hide a capture problem. |
| Buttons require unnaturally exact taps | Check touch slop, control-owned gestures, full hit identity, and whether a previous transition/deferred action is still busy. Use drift regression tests. |
| Dragging a list activates an item | Scroll cancellation/ownership regression. Verify movement threshold and release path against original hit. |
| Neighboring calculator/key value is entered | Release matched only action name or activated the release hit; preserve complete original control identity. |
| Old response reappears on Omni | Verify `set_launcher(False)` clears response/transcript state; submission's explicit preserve mode is the exception. |
| Navigation happens before acknowledgment | It bypassed `after_response`/`poll_response()` or used a backend timer instead of actual rendered/settled text. |
| Voice wheel movement is tiny | Farthest-start initialization regressed. Do not optimize it back to the previous current-selection shortest animation. |
| Existing app voice target is ambiguous | Duplicate titles are allowed; matcher falls through. Use a unique name/ID or let the agent clarify. Do not select the first arbitrary match. |
| Host process appears missing in sandbox `/proc` | Sandbox and desktop PID namespaces can differ. In this environment the running GUI process was visible only with appropriate host execution. Do not conclude it crashed from a sandbox-only PID check. |
| Test needs old immediate application behavior | Update frame/timing expectations; response-first action gating is intentional. Do not remove it to satisfy obsolete tests. |

When diagnosing mic issues, distinguish input enumeration, stream opening, worker decoding, partial display, final submission, and backend dispatch. The configured audio device is part of the environment, not a UI label. Keep logs useful without exposing API keys or dumping private profiles unnecessarily.

## 14. Git, publication, and local-only files

Before starting:

```sh
git status --short
git branch --show-current
git log -3 --oneline
```

Before a requested publication:

```sh
git fetch origin
git diff --check
# Run the tests in section 9.
# Stage reviewed source paths, not a blanket unreviewed directory tree.
git diff --cached --stat
git diff --cached --check
```

Commit a coherent change and push the requested branch only when authorized. A local commit is enough for the normal Pi deployer; a GitHub push is a distinct operation. Fetch/merge conflicts or new remote changes should be resolved without discarding existing local work or force-pushing the shared branch.

Files/directories intentionally local:

- `.env` / `.env.*` other than `.env.example`.
- `.venv/`, `sim/models/`, bytecode caches.
- `.omni-deployed.json` and machine profile data.
- Untracked `firmware/.pio/` build output.
- Untracked `eink-preview/` archived browser design reference.
- Screenshots, credential-bearing sync archives, and ad hoc scripts under `/tmp`.

The two untracked archive/build folders remained in `git status` after the last successful push. Their presence did not mean the active source was unsynced. Do not remove, publish, or stage them automatically. They are not both covered by `.gitignore`; staging a broad `firmware/` or `git add .` can accidentally include build output. Review the exact staged file list and ensure no credential literal was included.

Keep `.env` private when copying between machines. If a temporary archive contains it, give the archive restrictive permissions, never commit it, and remove that temporary copy after transfer. Copying an API key to the authorized local simulator does not mean publishing it.

## 15. Manual acceptance checklist for future UI changes

Use the subset relevant to the change, then widen checks only when there is an unresolved concern:

1. Main logo/wordmark, waveform, and text region render correctly at 480×800 in light and dark modes.
2. Home/selector morph and app open/back slides settle without a flash, orphaned hit areas, or permanent busy state.
3. Selector extends off screen; wheel can wrap, drag, scroll, snap, select a neighbor, and open the focused app.
4. Back, Settings rows, Calculator keys, keyboard keys, app buttons, toggles, and list items tolerate normal finger drift.
5. Dragging scrollable content does not activate its original or neighboring control. A cancelled fixed-button drag does not become a tap when returned to the original position.
6. Real microphone hold displays evolving partials; corrected hypotheses update cleanly. Silence, quick taps, cancelled captures, focus loss, and late events do not invent requests.
7. Submitted speech stays visible during backend wait; waiting arrows stop smoothly on real response/error arrival.
8. Responses progressively reveal/center/scroll, finish settling, and remain visible before effects occur. Escape can cancel the deferred action.
9. “Navigate to the settings page” works locally without a network call, displays acknowledgment, starts at the farthest app, rotates, focuses, and slides into Settings.
10. “Take me to the main agent view” returns cleanly; revisiting Omni later has no stale response.
11. “Switch to light mode,” “Make the font bigger,” and “Turn animations off” apply after acknowledgment and persist.
12. Time/date, note capture, arithmetic, and declared generated-app actions work through local matching; questions/negations/ambiguous names still fall through.
13. General Gemini responses and new composed apps validate. No raw JSON/analysis leaks into `say`, and no app is invented after an API error.
14. New generated app appears selected on the wheel; its inputs/buttons/lists share state and persist across restart.
15. Reduced motion remains usable and preserves ordering without animation.
16. Restarting sim/device loads the right profile and backend; copying source alone is not mistaken for restarting.
17. Relevant tests pass on desktop and, when deployed, on the Pi. A physical-device claim includes a verified deployed process, not only a successful SCP transfer.

## 16. Known boundaries and documentation precedence

This is a prototype, not a full phone OS. Current local commands do not implement arbitrary hardware brightness/network controls, timers, reminders, external services, or arbitrary app code. Unsupported requests may be handled/declined by Gemini within the strict component contract. Do not claim a local action exists merely because a keyword can be recognized.

The user wants UI changes in the real shared pygame flow. `eink-preview/` is a historical browser mockup; `firmware/.pio/` belongs to older hardware/build work. Neither is the active simulator. `firmware/phone.py` still contains legacy methods and recorder utilities; inspect which subclass/method the current entry point calls before editing it.

Some shorter READMEs retain old descriptions, including old demo modules/fixture paths, response-only history, or a claim that stub wait behavior follows preview delay. Prefer the current implementation, canonical contract, local command catalog, and this handoff's explicitly current behavior. Update stale text when it is directly relevant to the next change, rather than reviving old behavior.

No durable task depends on the original agent's tool session. Use commands and files, not old session IDs/PIDs. GUI launch, network access, Git writes, or writes to `~/.omni` can require host execution/approval under an agent sandbox. Follow that environment's actual permissions. Do not mistake sandbox restrictions for application failures or write around them through another tool.

### Suggested opening brief for the next agent

> Read `AGENTS.md` and `docs/UI_AGENT_HANDOFF.md`, inspect Git status, and open the shared pygame simulator with `sh sim/run.sh --backend gemini`. The current UI lives primarily in `firmware/native_ui.py`, with generated components in `firmware/components.py`, text animation in `firmware/transcript.py`, and explicit local voice commands in `firmware/local_commands.py`. Preserve live ASR text, response-before-action timing, farthest-start voice wheel navigation, touch-drift tolerance, and response clearing on return to Omni. Work locally first, use a scratch profile when needed, run relevant tests, and deploy over SCP from the development computer when requested. The Pi at `omni@100.124.54.78:~/Omni` is not a Git checkout. Do not push future changes unless the user requests it; never publish `.env` or generated machine/build artifacts.

When updating this handoff, refresh the observed commit/test counts and deployed manifest separately. Keep historical observations labeled; do not turn a one-time working configuration into a universal requirement. Documentation-only edits need link/example validation, not another hardware deployment.
