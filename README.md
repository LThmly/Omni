# Omni

Dedicated voice-and-touchscreen device. A standalone phone on a **Raspberry Pi 3 Model B** paints declarative JSON apps onto a **5" 800×480 HDMI LCD** with an **XPT2046** touchscreen. A finger drives it. A cloud call creates and edits those apps from speech. Product and hardware notes live in [`context/`](context/).

People can work in parallel. The shared surface is [`contract/`](contract/). The device shell, the simulator, and the cloud all read those fixtures. A change to a JSON shape lands in `contract/` in the same update as the code that uses it.

## Lanes

| Lane | Folder | Start here | Blocked on |
| :--- | :--- | :--- | :--- |
| Contract / modules | [`contract/`](contract/) | Module files and fixtures already describe the demo | Nothing |
| Device shell (Pi 3) | [`firmware/`](firmware/) | `sh firmware/demo.sh` on the Pi desktop | A board |
| Board bring-up | [`firmware/bringup/`](firmware/bringup/) | `sh firmware/demo.sh` wires touch, then the phone opens | A board |
| UI simulator | [`firmware/phone.py`](firmware/phone.py) | `sh sim/run.sh` opens the 480×800 window | pygame |
| Cloud agent | [`cloud/`](cloud/) | `try_turn.py` calls Gemini and returns one turn. `stub_server.py` is the offline stand-in | An API key, for the real call |

Claim a lane with a branch named after it: `firmware`, `sim`, `cloud`, `bringup`, `contract`.

## How a turn fits together

```
touch PTT hold  → local Vosk transcript (or recorded wav)
                → POST /v1/turn  { text or wav, registry }
                → { op: propose | mutate | say | navigate }
                → shell saves JSON and paints the phone
```

Touch interactions (`tap`, `scroll/swipe`, `toggle`, `inc`, `dec`) stay on the device and use the same actions as `mutate`. Both simulator and Pi support local Vosk recognition and typed requests; scripted speech previews remain available with `--speech demo`.

`propose` includes the whole app. The pygame controller saves it and selects it on the app wheel. `mutate` updates the app; `say` appears on the main screen. Use `--backend gemini` for direct Gemini calls or `--backend stub` for the HTTP path.

## Run the integration stub

From the repo root, in two terminals:

```bash
python3 cloud/stub_server.py
sh sim/run.sh
```

The phone is a pygame window, 480×800. The simulator and Pi share the same pygame UI. Defaults are Omni, Settings, Notes, Clock, and Calculator; the built-in generation demo works without a server. Add `--live` to use the stub at port 8787. No API key. On a Mac, install the window library once: `python3 -m venv .venv && .venv/bin/pip install pygame-ce`, then run with `.venv/bin/python`. The Pi package is `python3-pygame`.

## Demo modules

`checklist`, `scoreboard`, and `progress` cover the three scripts. `key_value` is spare. Specs are in [`contract/modules/`](contract/modules/).

Deploy committed source to the Pi with `python3 firmware/deploy.py omni@100.124.54.78 --backend gemini`; see [the shared workflow](firmware/README.md#edit-test-deploy). The deployment records its commit and file hashes; the Pi does not need a Git checkout.

Generated apps now follow the [v2 component contract](contract/README.md): Gemini classifies each request as a message, app creation, app update, or navigation. Apps bind fixed text/number/progress/toggle/list/input/button components to typed state and approved actions. Responses are validated before application, and intent metadata is persisted. Voice commands can open Settings, the main agent page, the app wheel, or an existing generated app.
