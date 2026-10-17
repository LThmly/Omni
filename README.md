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
| Cloud agent | [`cloud/`](cloud/) | `stub_server.py` is the offline `/v1/turn`. `try_turn.py` tests the real model | An API key, only for `try_turn.py` |

Claim a lane with a branch named after it: `firmware`, `sim`, `cloud`, `bringup`, `contract`.

## How a turn fits together

```
touch PTT hold  → wav on device
                → POST /v1/turn  { text or wav, registry }
                → { op: propose | mutate | say }
                → shell saves JSON and paints the phone
```

Touch interactions (`tap`, `scroll/swipe`, `toggle`, `inc`, `dec`) stay on the device and use the same actions as `mutate`. The simulator sends `text` instead of a wav, so UI work does not need the microphone.

`propose` includes the whole app. The shell shows the confirmation buttons (`[ Yes, create it ]` / `[ Cancel ]`), and a direct tap saves it. That second step does not call the model again.

## Run the integration stub

From the repo root, in two terminals:

```bash
python3 cloud/stub_server.py
sh sim/run.sh
```

The phone is a pygame window, 480×800. The simulator and Pi share the same pygame UI. Defaults are Omni, Settings, Notes, Clock, and Calculator; the built-in generation demo works without a server. Add `--live` to use the stub at port 8787. No API key. On a Mac, install the window library once: `python3 -m venv .venv && .venv/bin/pip install pygame-ce`, then run with `.venv/bin/python`. The Pi package is `python3-pygame`.

## Demo modules

`checklist`, `scoreboard`, and `progress` cover the three scripts. `key_value` is spare. Specs are in [`contract/modules/`](contract/modules/).
