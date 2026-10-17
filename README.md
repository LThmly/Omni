# Omni

Pocket e-ink device. A fixed firmware shell paints JSON apps. A cloud call creates and edits those apps from speech. Product and hardware notes live in [`context/`](context/).

People can work in parallel. The shared surface is [`contract/`](contract/). Firmware, the simulator, and the cloud all read those fixtures. A change to a JSON shape lands in `contract/` in the same update as the code that uses it.

## Lanes

| Lane | Folder | Start here | Blocked on |
| :--- | :--- | :--- | :--- |
| Contract / modules | [`contract/`](contract/) | Module files and fixtures already describe the demo | Nothing |
| Firmware shell | [`firmware/`](firmware/) | Boot the XIAO, then paint a fixture | A board. JSON is ready |
| Board bring-up | [`firmware/bringup/`](firmware/bringup/) | Prove display, wheel, mic, and write down the real refresh time | A board |
| E-ink simulator | [`sim/`](sim/) | Draw `contract/fixtures` at 400×300 | Nothing |
| Cloud agent | [`cloud/`](cloud/) | `stub_server.py` speaks `/v1/turn` today. Replace the keyword matcher with the model | An API key, only for the real model |

Claim a lane with a branch named after it: `firmware`, `sim`, `cloud`, `bringup`, `contract`.

## How a turn fits together

```
thumbwheel hold → wav on device
                → POST /v1/turn  { text or wav, registry }
                → { op: propose | mutate | say }
                → shell saves JSON and paints once
```

Thumbwheel edits (`scroll`, `toggle`, `inc`, `dec`) stay on the device and use the same actions as `mutate`. The simulator sends `text` instead of a wav, so UI work does not need the microphone.

`propose` includes the whole app. The shell shows the yes/no line, and a center press saves it. That second step does not call the model again.

## Run the integration stub

From the repo root, in two terminals:

```bash
python3 cloud/stub_server.py
python3 -m http.server 8080
```

Open `http://localhost:8080/sim/`. The stub listens on port 8787 and returns fixtures for "milk", "coffee", "ping pong", and "water". No API key.

## Demo modules

`checklist`, `scoreboard`, and `progress` cover the three scripts. `key_value` is spare. Specs are in [`contract/modules/`](contract/modules/).
