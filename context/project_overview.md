# Omni: Project Overview & Product Specification

## 1. Elevator Pitch
**Omni** is a dedicated, voice-and-touchscreen AI hardware companion built around a **Raspberry Pi 4** and a **Kuman 3.5" 480×320 HDMI touchscreen**. While devices like the Rabbit R1 focus on conversational answers or brittle web automations, Omni's core differentiator is **On-Demand Generative Apps**: instead of downloading apps from an app store or losing information in a chat log, Omni dynamically synthesizes persistent, bespoke micro-apps tailored to the user's exact needs the moment they ask for something new.

---

## 2. Core Value Proposition
- **Beyond Chatbots:** Pure voice assistants are ephemeral—once you ask a question, the UI disappears. Omni turns recurring intents into structured, interactive tools you can revisit and manipulate instantly with direct touch.
- **Zero-Friction App Creation:** Users don't write code or configure templates. Apps emerge naturally out of conversation when a capability gap is detected.
- **Responsive, Dedicated Hardware:** A 3.5" 480×320 60 FPS HDMI touchscreen paired with a Raspberry Pi 4 and USB microphone delivers a fluid, zero-latency direct-manipulation interface with vibrant visuals and instant tactile feedback.

---

## 3. Core User Experience & Interaction Flows

### Hardware Interaction Model
| Input / Output | Role in UX |
| :--- | :--- |
| **Touch Tap** | Select cards, toggle checkboxes, click confirmation buttons (`[ Yes, create it ]` / `[ Cancel ]`), or tap increment/decrement controls (`+` / `-`). |
| **Touch Drag / Swipe Up & Down** | Smooth inertial scrolling through app lists, long checklists, or metric views. |
| **Touch & Hold On-Screen PTT Button** | **Push-to-Talk (PTT):** Hold the on-screen mic action bar to record audio via the USB microphone; release to dispatch the turn request to the Omni Agent. |
| **3.5" HDMI Touchscreen (480×320, 60 FPS)** | Fluid 60Hz display for vibrant, high-contrast UI cards, animated agent waveforms, and instant 0ms local state updates without e-ink flash or refresh lag. |

### The "Main Agent View" (Home Screen)
The home screen splits into two primary zones:
1. **The Omni Agent Bar / Card:** Shows the agent's current state (Idle, Listening, Thinking, or Responding) with live animated feedback, the latest spoken prompt, and agent response.
2. **The Generated App Dock / Grid:** A touch-scrollable view of all micro-apps that Omni has created for the user.

### Flagship User Journey: "App Genesis"
1. **Natural Intent:** From the Main Agent View, the user touches and holds the on-screen PTT microphone button and speaks:
   > *"Add milk to my shopping list."*
2. **Intent Resolution & Gap Detection:**
   - Omni parses the user's intent (`action: add_item`, `domain: shopping_list`, `item: "Milk"`).
   - Omni checks its local registry of installed apps and sees no existing Shopping List app.
3. **Conversational Proposal:**
   - Omni displays on the 3.5" touchscreen:
     > *"Sure thing, but you don't have a shopping list app yet. Would you like me to make one?"*
   - Interactive options rendered below: `[ Yes, create it ]` (highlighted) / `[ Cancel ]`.
4. **Just-in-Time App Generation:**
   - The user taps **`[ Yes, create it ]`** (or speaks *"Yes"*).
   - Omni instantiates a bespoke **Shopping List** micro-app (using the pre-built `checklist` module layout and schema) and pre-populates it with the initial state (`["Milk"]`).
5. **Immediate Launch & Persistence:**
   - Omni transitions smoothly into the newly created **Shopping List** app showing `[ ] Milk`.
   - Later, when the user says *"Add eggs to my shopping list"*, Omni recognizes that the Shopping List app now exists and directly appends `"Eggs"` to that app's state without needing to regenerate it.

---

## 4. Proposed Technical Architecture

How this runs in the demo — how the Raspberry Pi 4 executes the shell, what the model is allowed to emit, the 60 FPS touch responsiveness, and the simulator — is detailed in [architecture.md](architecture.md).

Omni separates the **System Shell** from **Generative App Definitions**:

```
[USB Mic Audio] ──(Network)──> [Cloud / Backend Agent Pipeline]
                                  │  1. Speech-to-Text (STT)
                                  │  2. Intent Router (Existing App vs. Missing Capability)
                                  │  3. App Generator / State Mutator (LLM Structured Output)
                                  ▼
[Raspberry Pi 4 Shell] <──(JSON)── [App Spec + State Payload]
   ├── 480×320 60Hz HDMI GUI Renderer (Chromium Kiosk / Python GUI)
   ├── Local App Registry & State Store (~/.omni/registry.json)
   └── XPT2046 Touch Event Handler (Tap, Swipe, Hold-to-Talk)
```

### How a Generated App is Represented
Each generated app is a lightweight, structured **JSON App Specification** stored in local flash and rendered by the shell engine on the Raspberry Pi 4. An app consists of:
- **Metadata:** `id`, `title`, `icon`, `description`, `created_at`
- **State Schema & Data:** Key-value or list state (e.g., `items: [{ label: "Milk", checked: false }]`, `count: 0`, `score_a: 11`)
- **UI Primitives (Touch Optimized):**
  - `Header`: App title and status summary
  - `Checklist`: Toggleable items with tap-to-check and swipe-to-scroll
  - `Counter / Scoreboard`: Large numeric displays with tap `+` / `-` buttons
  - `KeyValueList` / `Cards`: Read-only or actionable info cards
  - `ActionButtons`: Quick-add triggers mapped to local state mutations (e.g., `+8 oz`, `+16 oz`)
- **Voice Hooks:** Natural-language intents that route directly to this app's state (e.g., adding/removing items, resetting counters, logging entries).

---

## 5. High-Impact Hackathon Demo Scenarios

1. **The Shopping List (List + State Persistence)**
   - *Prompt 1:* *"Add milk to my shopping list."* -> Proposes & generates the **Shopping List** app with `"Milk"`.
   - *Prompt 2:* *"Also add coffee and bread."* -> Recognizes the newly created app and updates its state immediately.
   - *Hardware interaction:* User taps on the screen to check off `"Milk"` or swipes through items.
2. **The Scorekeeper / Tracker (Counter Primitives)**
   - *Prompt:* *"Keep score for ping pong between me and Alex."* -> Proposes & generates a **Ping Pong Scoreboard** app.
   - *Hardware interaction:* User taps on-screen `+` / `-` buttons to increment scores or speaks *"Point for Alex"*.
3. **The Habit / Water Logger (Quick Metric App)**
   - *Prompt:* *"Log that I drank 16 ounces of water towards a 64-ounce daily goal."* -> Generates a **Hydration Tracker** app with a progress bar and quick-tap `+8 oz` / `+16 oz` buttons.ogress bar and quick `+8 oz` / `+16 oz` buttons.
