# Omni: Project Overview & Product Specification

## 1. Elevator Pitch

**Omni** is a dedicated, voice-and-touchscreen AI hardware companion built around a **Raspberry Pi 3 Model B** and a **5" 800×480 HDMI LCD with an XPT2046 touchscreen**. While devices like the Rabbit R1 focus on conversational answers or brittle web automations, Omni's core differentiator is **On-Demand Generative Apps**: instead of downloading apps from an app store or losing information in a chat log, Omni dynamically synthesizes persistent, bespoke micro-apps tailored to the user's exact needs the moment they ask for something new.

---

## 2. Core Value Proposition

- **Beyond Chatbots:** Pure voice assistants are ephemeral. Once you ask a question, the UI disappears. Omni turns recurring intents into structured, interactive tools you can revisit and manipulate with touch.
- **Zero-Friction App Creation:** Users don't write code or configure templates. Apps emerge from conversation when a capability is missing.
- **A phone, not a desktop:** A finger on the XPT2046 glass drives a portrait app. Tap, drag, and hold are the whole interaction. The panel is 800×480; the app is 480×800 and turns to fill the glass.

---

## 3. Core User Experience & Interaction Flows

### Hardware Interaction Model

| Input / Output | Role in UX |
| :--- | :--- |
| **Touch tap** | Select cards, toggle checkboxes, click confirmation buttons (`[ Yes, create it ]` / `[ Cancel ]`), or tap increment and decrement controls (`+` / `−`). |
| **Touch drag** | Scroll app lists, long checklists, or metric views. |
| **Touch and hold the on-screen talk bar** | **Push-to-talk:** hold to record from the USB microphone; release to send the turn. The simulator sends typed text until the microphone path exists. |
| **Portrait phone (480×800)** | One full-screen app at a time: the mark, a vertical list, and push-to-talk at the bottom. The stack stands on its side so this fills the glass. |

### The Main Agent View

The home screen has two zones:

1. **The Omni agent bar.** Idle, listening, thinking, or responding, plus the latest line from the agent.
2. **The app list.** The micro-apps Omni has created, in one column, each row large enough to hit with a finger.

### Flagship User Journey: App Genesis

1. **Natural intent.** From home, the user holds the talk bar and speaks:
   > *"Add milk to my shopping list."*
2. **Gap detection.** Omni parses the intent and finds no shopping list in the local registry.
3. **Proposal.** The panel shows:
   > *"You don't have a shopping list yet. Make one?"*
   with `[ Yes, create it ]` and `[ Cancel ]`.
4. **Creation.** The user taps **Yes, create it**. Omni stores a `checklist` app whose first item is Milk.
5. **Persistence.** The shopping list opens. A later *"Add eggs to my shopping list"* appends Eggs to that same app.

---

## 4. Proposed Technical Architecture

How the Pi runs the shell, what the model is allowed to emit, and how the simulator stays in lockstep is in [architecture.md](architecture.md).

```
[USB mic / simulator text] ──> [Cloud turn]
                                  │  1. Speech-to-text
                                  │  2. Existing app vs missing capability
                                  │  3. Structured propose / mutate / say
                                  ▼
[Raspberry Pi 3 shell] <── JSON ── [App spec + state]
   ├── Portrait phone (sim/, fullscreen via firmware/install.sh)
   └── Local app registry
```

Each generated app is a JSON document:

- **Metadata:** `id`, `module`, `title`
- **State:** lists and counters (`items`, `sides`, `value` / `goal`)
- **UI the shell already knows how to paint:** checklist, scoreboard, progress, key/value rows, confirm buttons
- **Voice:** later utterances route to that app's actions

---

## 5. High-Impact Hackathon Demo Scenarios

1. **Shopping list**
   - *"Add milk to my shopping list."* proposes a checklist with Milk.
   - *"Also add coffee and bread."* appends to that app.
   - Tap a row to check it off.
2. **Scorekeeper**
   - *"Keep score for ping pong between me and Alex."* proposes a scoreboard.
   - Tap `+` / `−`, or say *"Point for Alex"*.
3. **Water log**
   - *"Log that I drank 16 ounces of water towards a 64-ounce daily goal."* proposes a progress app with `+8 oz` and `+16 oz`.
