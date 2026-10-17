# Omni: Project Overview & Product Specification

## 1. Elevator Pitch
**Omni** is a pocketable, voice-and-thumbwheel AI hardware companion built around a tri-color E-Ink display. While devices like the Rabbit R1 focus on conversational answers or brittle web automations, Omni's core differentiator is **On-Demand Generative Apps**: instead of downloading apps from an app store or losing information in a chat log, Omni dynamically synthesizes persistent, bespoke micro-apps tailored to the user's exact needs the moment they ask for something new.

---

## 2. Core Value Proposition
- **Beyond Chatbots:** Pure voice assistants are ephemeral—once you ask a question, the UI disappears. Omni turns recurring intents into structured, interactive tools you can revisit with a flick of the thumbwheel.
- **Zero-Friction App Creation:** Users don't write code or configure templates. Apps emerge naturally out of conversation when a capability gap is detected.
- **Calm, Intentional Hardware:** A 4.2" Black/White/Red E-Ink screen paired with a tactile 3-way thumbwheel and push-to-talk microphone delivers a distraction-free, high-contrast interface designed for quick, single-handed interactions.

---

## 3. Core User Experience & Interaction Flows

### Hardware Interaction Model
| Input / Output | Role in UX |
| :--- | :--- |
| **Thumbwheel Up / Down** | Cycle through apps on the launcher, scroll lists, increment/decrement values, or switch between dialog choices (`Yes` / `No`). |
| **Thumbwheel Center Push (Short Press)** | Select highlighted item, toggle checkboxes, or confirm prompts. |
| **Thumbwheel Center Push (Long Press / Hold)** | **Push-to-Talk (PTT):** Activates the I2S MEMS microphone from anywhere in the OS to talk to the Omni Agent. |
| **4.2" Tri-Color E-Ink (B/W/Red)** | Crisp, daylight-readable UI. **Black/White** for primary layout and typography; **Red** reserved for active selection highlights, recording status, alerts, and key accents. |

### The "Main Agent View" (Home Screen)
The home screen splits into two primary zones:
1. **The Omni Agent Bar / Card:** Shows the agent's current state (Idle, Listening, Thinking, or Responding) along with the latest spoken prompt and agent response.
2. **The Generated App Dock / List:** A thumbwheel-scrollable list or grid of all micro-apps that Omni has created for the user.

### Flagship User Journey: "App Genesis"
1. **Natural Intent:** From the Main Agent View, the user holds the thumbwheel and speaks:
   > *"Add milk to my shopping list."*
2. **Intent Resolution & Gap Detection:**
   - Omni parses the user's intent (`action: add_item`, `domain: shopping_list`, `item: "Milk"`).
   - Omni checks its local registry of installed apps and sees no existing Shopping List app.
3. **Conversational Proposal:**
   - Omni displays on the E-Ink screen:
     > *"Sure thing, but you don't have a shopping list app yet. Would you like me to make one?"*
   - Interactive options rendered below: `[ Yes, create it ]` (highlighted in Red) / `[ No, cancel ]`.
4. **Just-in-Time App Generation:**
   - The user clicks the thumbwheel (or says *"Yes"*).
   - Omni generates a bespoke **Shopping List** micro-app (UI layout, data schema, and thumbwheel actions) and pre-populates it with the initial state (`["Milk"]`).
5. **Immediate Launch & Persistence:**
   - Omni transitions directly into the newly created **Shopping List** app showing `[ ] Milk`.
   - Later, when the user says *"Add eggs to my shopping list"*, Omni recognizes that the Shopping List app now exists and directly appends `"Eggs"` to that app's state without needing to regenerate it.

---

## 4. Proposed Technical Architecture

How this runs in the demo — who compiles, what the model is allowed to emit, the e-ink refresh budget, and the simulator — is decided in [architecture.md](architecture.md).

Because the **Seeed Studio XIAO ESP32S3 Plus** (with 8MB PSRAM and Wi-Fi) cannot recompile C++ firmware on the fly, Omni separates the **System Shell** from **Generative App Definitions**:

```
[I2S Mic Audio] ──(Wi-Fi)──> [Cloud / Backend Agent Pipeline]
                                  │  1. Speech-to-Text (STT)
                                  │  2. Intent Router (Existing App vs. Missing Capability)
                                  │  3. App Generator / State Mutator (LLM Structured Output)
                                  ▼
[ESP32-S3 Runtime] <──(JSON)── [App Spec + State Payload]
   ├── E-Ink Declarative UI Renderer (400x300 B/W/Red)
   ├── Local App Registry & State Store (Flash / LittleFS + PSRAM)
   └── Thumbwheel Event Dispatcher (Up / Down / Push / Hold)
```

### How a Generated App is Represented
Each generated app is a lightweight, structured **JSON App Specification** stored in Flash/PSRAM and rendered by a native C++ E-Ink engine on the ESP32-S3. An app consists of:
- **Metadata:** `id`, `title`, `icon`, `description`, `created_at`
- **State Schema & Data:** Key-value or list state (e.g., `items: [{ label: "Milk", checked: false }]`, `count: 0`, `score_a: 11`)
- **UI Primitives (E-Ink Optimized):**
  - `Header`: App title and status summary
  - `Checklist`: Toggleable items navigated via Up/Down/Push
  - `Counter / Scoreboard`: Numeric displays incremented/decremented via Up/Down
  - `KeyValueList` / `Cards`: Read-only or actionable info cards
  - `ActionButtons`: Custom triggers mapped to local state mutations or agent prompts
- **Voice Hooks:** Natural-language intents that route directly to this app's state (e.g., adding/removing items, resetting counters, logging entries).

---

## 5. High-Impact Hackathon Demo Scenarios

1. **The Shopping List (List + State Persistence)**
   - *Prompt 1:* *"Add milk to my shopping list."* -> Proposes & generates the **Shopping List** app with `"Milk"`.
   - *Prompt 2:* *"Also add coffee and bread."* -> Recognizes the newly created app and updates its state immediately.
   - *Hardware interaction:* User scrolls with the thumbwheel and clicks to check off `"Milk"`.
2. **The Scorekeeper / Tracker (Counter Primitives)**
   - *Prompt:* *"Keep score for ping pong between me and Alex."* -> Proposes & generates a **Ping Pong Scoreboard** app.
   - *Hardware interaction:* User uses the thumbwheel to increment scores or speaks *"Point for Alex"*.
3. **The Habit / Water Logger (Quick Metric App)**
   - *Prompt:* *"Log that I drank 16 ounces of water towards a 64-ounce daily goal."* -> Generates a **Hydration Tracker** app with a progress bar and quick `+8 oz` / `+16 oz` buttons.
