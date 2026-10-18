# Omni Architecture (ESP32 & E-Ink)

## Overview

The standalone device runtime runs on a **Seeed Studio XIAO ESP32S3 Plus** driving an **Adafruit 6382 (4.2" 400×300 Tri-Color Black/White/Red SSD1683 E-Ink display)** via an **Adafruit 4224 eInk Breakout Friend**.

User input is driven by a **Same Sky TS43-135255-10-BK-200-SMT-TR 3-way thumbwheel navigation switch** (Up, Down, Center Push with click and hold-to-talk) and an **Adafruit 6049 I2S MEMS microphone**.

The firmware is a fixed C++ system shell flashed once to the ESP32. At runtime, dynamic applications and state mutations are exchanged as structured JSON documents adhering to [`contract/`](../contract/).

Three runtimes share that contract:

| Runtime | Job | When it runs |
| :--- | :--- | :--- |
| **ESP32-S3 E-Ink shell** | Captures audio/input, executes local actions, paints the E-Ink panel | On the physical board |
| **Laptop / Pygame simulator** | Rapid UI and speech testing at 480×800 or 400×300 | Development and CI |
| **Cloud agent / Gemini** | Speech-to-text, intent classification, and one structured turn (`propose`, `mutate`, `say`, `navigate`) | Whenever the user speaks |

---

## Why the Model Does Not Generate Arbitrary Code

The XIAO ESP32-S3 Plus cannot host a C++ compiler or safely run untrusted interpreted code. A model attempting to emit C++ or JavaScript would risk crashes, layout corruption, and sluggish execution.

The firmware ships with a declarative component catalog (`checklist`, `scoreboard`, `progress`, `key_value`, and `composed`). The model outputs structured JSON specifying which components to render and their bound state fields.

---

## What Crosses the Network

One structured endpoint: `POST /v1/turn` (or direct Gemini 1.5/2.0 API call):

```json
{
  "text": "Add milk to my shopping list.",
  "wav_base64": "...",
  "registry": [],
  "focused_app_id": null
}
```

The response is one of four operations defined in [`contract/turn.schema.json`](../contract/turn.schema.json):

1. `propose` — proposes a new app. The shell displays a confirmation card (`[ Yes, create it ]` / `[ Cancel ]`).
2. `mutate` — actions on an existing app (`set`, `increment`, `toggle`, `append`, `clear`, `remove_checked`).
3. `say` — text spoken/displayed by the agent without altering app state.
4. `navigate` — opens a destination (`agent`, `apps`, `settings`, `notes`, `clock`, `calculator`, or `app_id`).

If the network is unavailable or unconfigured, the ESP32 firmware features an **Offline Demo Mode** that cycles through the flagship hackathon scenarios automatically upon PTT release.

---

## What Stays on the Device

Thumbwheel input never waits on the network:

- Scrolling Up/Down updates the selected item or active app.
- Center-clicking toggles checkboxes, increments counters, or confirms proposals instantly.
- The app registry is persisted in the ESP32-S3's Flash memory (via LittleFS or NVS Preferences) and 8MB PSRAM.
- Voice goes to the cloud and returns the exact same declarative operations.

---

## The E-Ink Display Constraints

The panel is a 4.2" 400×300 tri-color SSD1683 (Adafruit 6382). Tri-color full refresh cycles take several seconds.

Firmware design mitigations:
- **Input Coalescing:** Consecutive rapid thumbwheel clicks coalesce so the display only refreshes once motion pauses.
- **Selective Red Accents:** Red is reserved for active selection highlights, the PTT recording mark, alerts, and confirmation buttons.
- **State Feedback:** The agent bar displays current state (`IDLE`, `LISTENING`, `THINKING`, `RESPONDING`) with clean typography.
- **Hardware BUSY Polling:** Non-blocking check of the `BUSY` line (`D9` / GPIO8) ensures SPI transfers never collide.

---

## Navigation Button Interaction Model

The Same Sky TS43 thumbwheel switch connects to GND with internal pull-ups:
- **Up (`D4` / GPIO5):** Navigates up through menu items, lists, or teams.
- **Down (`D3` / GPIO4):** Navigates down through menu items, lists, or teams.
- **Center Push (`D19` / GPIO11):**
  - **Short Click (< 400ms):** Selects highlighted item, toggles checkboxes, increments score, confirms dialog.
  - **Long Press / Hold (>= 500ms):** **Push-to-Talk (PTT)**. While held, I2S microphone records audio. Upon release, turn request is sent.
