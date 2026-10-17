# Omni

Dedicated voice-and-touchscreen device. A standalone shell on a **Raspberry Pi 4** paints declarative JSON apps onto a **Kuman 3.5" 480×320 HDMI touchscreen**. A cloud call creates and edits those apps from speech. Product and hardware notes live in [`context/`](context/).

People can work in parallel. The shared surface is [`contract/`](contract/). The device shell, the simulator, and the cloud all read those fixtures. A change to a JSON shape lands in `contract/` in the same update as the code that uses it.

## Lanes

| Lane | Folder | Start here | Blocked on |
| :--- | :--- | :--- | :--- |
| Contract / modules | [`contract/`](contract/) | Module files and fixtures already describe the demo | Nothing |
| Device shell (Pi 4) | [`firmware/`](firmware/) | Boot Pi 4 & 3.5" HDMI touchscreen, paint a fixture | A board. JSON is ready |
| Board bring-up | [`firmware/bringup/`](firmware/bringup/) | HDMI display & XPT2046 touch configuration | A board |
| UI Simulator | [`sim/`](sim/) | Render `contract/fixtures` at 480×320 / 400×300 | Nothing |
| Cloud agent | [`cloud/`](cloud/) | `stub_server.py` is the offline `/v1/turn`. `try_turn.py` tests the real model | An API key, only for `try_turn.py` |

Claim a lane with a branch named after it: `firmware`, `sim`, `cloud`, `bringup`, `contract`.

## How a turn fits together

```
touch PTT hold  → wav on device
                → POST /v1/turn  { text or wav, registry }
                → { op: propose | mutate | say }
                → shell saves JSON and paints at 60 FPS
```

Touch interactions (`tap`, `scroll/swipe`, `toggle`, `inc`, `dec`) stay on the device and use the same actions as `mutate`. The simulator sends `text` instead of a wav, so UI work does not need the microphone.

`propose` includes the whole app. The shell shows the confirmation buttons (`[ Yes, create ]` / `[ Cancel ]`), and a direct tap saves it. That second step does not call the model again.

## Run the integration stub

From the repo root, in two terminals:

```bash
python3 cloud/stub_server.py
python3 -m http.server 8080
```

Open `http://localhost:8080/sim/`. The stub listens on port 8787 and returns fixtures for "milk", "coffee", "ping pong", and "water". No API key.

## Demo modules

`checklist`, `scoreboard`, and `progress` cover the three scripts. `key_value` is spare. Specs are in [`contract/modules/`](contract/modules/).
