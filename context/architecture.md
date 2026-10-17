# Omni Architecture (Hackathon)

## Decision

The device runtime runs standalone on a **Raspberry Pi 4** driving a **Kuman 3.5" 480×320 HDMI touchscreen**.

The core system architecture remains declarative: the model does not generate arbitrary executable code (no raw C++, Python, or unrestricted scripts synthesized live). The model outputs structured JSON documents adhering to [`contract/`](../contract/), selecting pre-built UI modules and populating their state fields.

Three runtimes share that contract document:

| Runtime | Job | When it runs |
| :--- | :--- | :--- |
| **Pi 4 Shell** | Fullscreen 480×320 HDMI GUI, touch event handling, USB microphone capture, local state storage | Live demo on stage |
| **Browser simulator** | Renders the exact same JSON at 480×320; simulates touch taps and swipes | Development without hardware |
| **Cloud agent** | Speech-to-text, intent routing, structured LLM turn response (`propose`, `mutate`, `say`) | Whenever the user speaks |

---

## Why the model does not generate arbitrary code

Even though a Raspberry Pi 4 has full Linux and a Python/C++ toolchain, allowing an LLM to generate arbitrary executable code live on stage introduces severe latency, unpredictable dependencies, UI layout breakage, and security risks.

Instead, the device ships with a robust, pre-styled **Module Catalog**. The LLM simply returns clean, structured data defining which module to instantiate and what data to display.

---

## What crosses the network

One unified HTTPS endpoint: `POST /v1/turn`.
The payload carries either audio (WAV base64 from the USB mic) or plain text (from the dev simulator), along with the current device app registry:

```json
{
  "text": "Add milk to my shopping list.",
  "registry": [],
  "focused_app_id": null
}
```

The cloud agent responds with one of three operations defined in [`contract/turn.schema.json`](../contract/turn.schema.json):
- `propose` — Proposes a new app (module name, title, initial state). The shell shows an on-screen confirmation card (`[ Yes, create ]` / `[ Cancel ]`).
- `mutate` — Applies an array of operations to an existing app (`toggle`, `append`, `inc`, `dec`, `add`).
- `say` — A conversational line displayed in the Agent Bar when no app state changes.

If the model returns an invalid payload, the server retries once, then returns a fallback `say` message. The device shell never crashes from model formatting anomalies.

---

## What stays on the device

**Touch interactions never wait on the network:**
* Tapping a checkbox toggles it immediately (0ms latency).
* Tapping `+` or `-` increments or decrements scores instantly.
* Swiping or dragging smoothly scrolls the viewport.
* Local mutations update the on-disk JSON registry (`~/.omni/registry.json`) and refresh the screen at 60 FPS.

Voice intents still go to the cloud for natural language parsing, but return as the exact same atomic operations (`toggle`, `append`, etc.).

---

## The Display & UI Experience

With the shift to the **Kuman 3.5" 480×320 60Hz HDMI Display**:
* **High Refresh Rate:** Video updates render at **60 FPS** with zero E-Ink refresh flashing or multi-second latency.
* **Rich Color Palette:** Vibrant modern aesthetics (dark mode, crisp typography, colored status badges) replace the 3-color E-Ink restrictions.
* **Animated Agent States:** The Omni Agent Bar dynamically transitions between states:
  * `Idle`: Minimal unobtrusive status dot.
  * `Listening`: Active audio waveform / pulse reacting to voice.
  * `Thinking`: Subtle animated spinner or pulse.
  * `Responding`: Clean speech bubble with agent text.

---

## Module Catalog

The hackathon catalog covers the three core showcase scenarios:

| Module | UI Elements | Local Touch Interactions | Demo Line |
| :--- | :--- | :--- | :--- |
| `checklist` | Title, scrollable list of rows, check boxes | **Tap row:** toggle check<br>**Swipe:** scroll list | *"Add milk to my shopping list."* |
| `scoreboard` | Two player names, large numeric scores | **Tap `+` / `-`:** increment/decrement | *"Keep score for ping pong between me and Alex."* |
| `progress` | Metric label, current value, target, progress bar | **Tap quick-add buttons:** `+8 oz`, `+16 oz` | *"Log 16 ounces toward 64."* |
| `key_value` | Read-only styled cards / rows | **Swipe:** scroll through attributes | Spare / fallback scenario |

---

## Touchscreen Interaction Model

1. **Touch Navigation:** Tapping selects cards, buttons, or checkboxes; finger drag scrolls long lists.
2. **Push-to-Talk (PTT):** A persistent microphone action bar is rendered at the bottom of the screen. 
   * **Touch & Hold:** Starts audio capture from the USB microphone.
   * **Release:** Finalizes WAV audio and dispatches `POST /v1/turn`.
3. **App Genesis Confirmation:** When the cloud returns `propose`, the screen displays a modal card:
   * Tapping **`[ Yes, create it ]`** commits the app to the local registry and transitions into it.
   * Tapping **`[ Cancel ]`** dismisses the proposal.

---

## Cut line

* **In scope:** Raspberry Pi 4 shell (Chromium kiosk or Python GUI), Kuman 3.5" HDMI touch driver, USB microphone recording, 60 FPS touch interactions, cloud turn endpoint, module catalog.
* **Out of scope:** On-device local LLM execution, custom PCB fabrication, arbitrary code generation.
