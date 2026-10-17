# Omni Architecture (Hackathon)

## Decision

The device runtime runs on a **Raspberry Pi 3 Model B** driving a **5" 800×480 HDMI LCD** with an **XPT2046** touchscreen.

The shell runs as one fullscreen pygame window on Raspberry Pi OS. `firmware/install.sh` opens it at login and keeps it there until you quit. The app is a 480×800 portrait phone. The panel is 800×480, so the kiosk turns that window 90° and the stack stands with its right edge up. A finger on the glass is the input: tap, drag, and hold, the same gestures as a phone.

A bare-metal image would have to reimplement HDMI timing, the SPI touchscreen, and Wi-Fi before any UI could appear. The product work is the shell, so the shell runs on Raspberry Pi OS.

The model does not generate arbitrary executable code. It outputs structured JSON from [`contract/`](../contract/), selecting pre-built UI modules and filling their state.

Three runtimes share that contract:

| Runtime | Job | When it runs |
| :--- | :--- | :--- |
| **Pi 3 shell** | Fullscreen portrait phone, finger input, local state | On the panel |
| **Laptop window** | The same pygame phone, upright, at 480×800 | Menu work without the board |
| **Cloud agent** | Speech-to-text and one `propose`, `mutate`, or `say` | Whenever the user speaks |

The laptop window is that phone, shown upright. On the Pi the same window is turned to fill the glass.

---

## Why the model does not generate arbitrary code

The Pi can run whatever we install, and letting the model emit live Python or JavaScript would mean latency, missing dependencies, broken layout, and a device that can be talked into running the wrong thing.

The device ships with a module catalog. The model returns which module to show and what data to put in it.

---

## What crosses the network

One endpoint: `POST /v1/turn`.
The body is audio (`wav_base64`) or plain text from the simulator, plus the apps already on the device:

```json
{
  "text": "Add milk to my shopping list.",
  "registry": [],
  "focused_app_id": null
}
```

The response is one of three operations in [`contract/turn.schema.json`](../contract/turn.schema.json):

- `propose` — a new app. The shell shows `[ Yes, create it ]` / `[ Cancel ]`.
- `mutate` — actions on an app that already exists (`toggle`, `append`, `inc`, `dec`, `add`).
- `say` — a line in the agent bar when no app changes.

An invalid payload is retried once on the server, then replaced with a fallback `say`. The shell does not crash on a bad model reply.

---

## What stays on the device

Touch does not wait on the network:

- Tapping a row toggles it.
- Tapping `+` or `−` changes a score.
- Dragging scrolls a list.
- The registry is the apps on the device, stored in `~/.omni/registry.json` on the laptop and on the Pi.

Voice still goes to the cloud and comes back as the same actions.

---

## The display

The panel is an 800×480 HDMI LCD. Touch is the XPT2046 on the GPIO header. Once Raspberry Pi OS loads the `ads7846` overlay, a finger is a normal pointer and the phone does not carry its own touch driver.

The product UI is a portrait phone, 480×800: the arrow mark, the Neuropolitical “omni” wordmark, an agent line, a vertical list of apps, and push-to-talk at the bottom. Targets are large enough for a finger. The kiosk turns that phone onto the landscape glass. The laptop window shows the same phone upright, and the mouse stands in for the finger.

---

## Module catalog

| Module | UI | Local touch | Demo line |
| :--- | :--- | :--- | :--- |
| `checklist` | Title and rows | Tap a row to toggle. Drag to scroll | *"Add milk to my shopping list."* |
| `scoreboard` | Two names and scores | Tap `+` / `−` | *"Keep score for ping pong between me and Alex."* |
| `progress` | Value, goal, bar, quick add | Tap `+8 oz` / `+16 oz` | *"Log 16 ounces toward 64."* |
| `key_value` | Label / value rows | Tap to focus. Drag to scroll | Spare |

---

## Touch

1. A finger tap selects a card, a row, or a button. A drag scrolls. Nothing on screen expects a keyboard.
2. Push-to-talk is the bar at the bottom of the phone. Hold starts a turn. Release sends it. Until the microphone is connected, release sends a canned line. On a laptop, typed text and Enter send a turn.
3. On `propose`, a finger on `[ Yes, create it ]` stores the app and opens it. `[ Cancel ]` dismisses the card. Neither tap calls the model again.

---

## Cut line

* **In scope:** Pi 3 Model B phone on Raspberry Pi OS, XPT2046 touch, login autostart, the pygame phone (laptop and panel), cloud turn endpoint, module catalog.
* **Out of scope:** A bare-metal image, an on-device LLM, custom PCB, arbitrary code generation.
