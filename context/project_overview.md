# Omni: Project Overview & Product Specification

## 1. Elevator Pitch

**Omni** is a dedicated, pocketable, voice-and-thumbwheel AI hardware companion built around a **Seeed Studio XIAO ESP32S3 Plus** and a **4.2" 400×300 Tri-Color (Black/White/Red) E-Ink display**. While devices like the Rabbit R1 focus on conversational answers or brittle web automations, Omni's core differentiator is **On-Demand Generative Apps**: instead of downloading apps from an app store or losing information in a chat log, Omni dynamically synthesizes persistent, bespoke micro-apps tailored to the user's exact needs the moment they ask for something new.

---

## 2. Core Value Proposition

- **Beyond Chatbots:** Pure voice assistants are ephemeral—once you ask a question, the UI disappears. Omni turns recurring intents into structured, interactive tools you can revisit with a flick of the thumbwheel.
- **Zero-Friction App Creation:** Users don't write code or configure templates. Apps emerge naturally out of conversation when a capability gap is detected.
- **Calm, High-Contrast Hardware:** A 4.2" Black/White/Red E-Ink screen paired with a tactile 3-way thumbwheel and push-to-talk microphone delivers a distraction-free, sunlight-readable interface designed for quick, single-handed interactions.

---

## 3. Core User Experience & Interaction Flows

### Hardware Interaction Model

| Input / Output | Role in UX |
| :--- | :--- |
| **Thumbwheel Up / Down** | Cycle through apps on the launcher, scroll lists, increment/decrement values, or switch between dialog choices (`[ Yes, create it ]` / `[ Cancel ]`). |
| **Thumbwheel Center Push (Short Press)** | Select highlighted item, toggle checkboxes, trigger button actions, or confirm prompts. |
| **Thumbwheel Center Push (Long Press / Hold)** | **Push-to-Talk (PTT):** Activates the I2S MEMS microphone from anywhere in the OS to talk to the Omni Agent. |
| **4.2" Tri-Color E-Ink (B/W/Red)** | Crisp, daylight-readable UI. **Black/White** for primary layout and typography; **Red** reserved for active selection highlights, recording status, alerts, and key accents. |

### The "Main Agent View" (Home Screen)

The home screen splits into two primary zones:
1. **The Omni Agent Bar / Card:** Shows the agent's current state (Idle, Listening, Thinking, or Responding) along with the latest spoken prompt and agent response.
2. **The App List / Dock:** A thumbwheel-scrollable list of all micro-apps installed or created for the user.

### Flagship User Journey: "App Genesis"

1. **Natural Intent:** From the Main Agent View, the user holds the thumbwheel and speaks:
   > *"Add milk to my shopping list."*
2. **Intent Resolution & Gap Detection:**
   - Omni parses the user's intent (`action: create_app`, `domain: shopping_list`, `item: "Milk"`).
   - Omni checks its local registry of installed apps and sees no existing Shopping List app.
3. **Conversational Proposal:**
   - Omni displays on the E-Ink screen:
     > *"You don't have a shopping list yet. Would you like me to make one?"*
   - Interactive options rendered below: `[ Yes, create it ]` (highlighted in Red) / `[ Cancel ]`.
4. **Just-in-Time App Generation:**
   - The user clicks the thumbwheel (or says *"Yes"*).
   - Omni generates a bespoke **Shopping List** micro-app and pre-populates it with the initial state (`["Milk"]`).
5. **Immediate Launch & Persistence:**
   - Omni transitions directly into the newly created **Shopping List** app showing `[ ] Milk`.
   - Later, when the user says *"Add eggs to my shopping list"*, Omni recognizes that the Shopping List app exists and directly appends `"Eggs"` to that app's state without regenerating it.

---

## 4. Proposed Technical Architecture

Because the **Seeed Studio XIAO ESP32S3 Plus** (with 16MB Flash, 8MB PSRAM and Wi-Fi) cannot recompile C++ firmware on the fly, Omni separates the **System Shell** from **Generative App Definitions**:

```
[I2S Mic Audio / Text] ──(Wi-Fi)──> [Cloud / Gemini Agent Pipeline]
                                         │  1. Speech-to-Text (STT)
                                         │  2. Intent Router (Existing App vs. Missing Capability)
                                         │  3. App Generator / State Mutator (Structured Output)
                                         ▼
[ESP32-S3 Firmware Shell] <──(JSON)── [App Spec + State Payload]
   ├── E-Ink Declarative UI Renderer (Adafruit ThinkInk 4.2" 400×300 B/W/Red)
   ├── Local App Registry & State Store (Flash / NVS + PSRAM)
   └── Thumbwheel Event Dispatcher (Up / Down / Click / PTT Hold)
```

Each generated app is a lightweight, structured **JSON App Specification** stored in Flash/PSRAM and rendered by the native C++ E-Ink engine on the ESP32-S3.

---

## 5. High-Impact Hackathon Demo Scenarios

1. **The Shopping List (List + State Persistence)**
   - *Prompt 1:* *"Add milk to my shopping list."* -> Proposes & generates the **Shopping List** app with `"Milk"`.
   - *Prompt 2:* *"Also add coffee and bread."* -> Recognizes the existing app and appends items immediately.
   - *Hardware interaction:* User scrolls with the thumbwheel and clicks to check off `"Milk"`.
2. **The Scorekeeper / Tracker (Counter Primitives)**
   - *Prompt:* *"Keep score for ping pong between me and Alex."* -> Proposes & generates a **Ping Pong Scoreboard** app.
   - *Hardware interaction:* User uses the thumbwheel to switch teams and clicks to increment scores, or speaks *"Point for Alex"*.
3. **The Habit / Water Logger (Quick Metric App)**
   - *Prompt:* *"Log that I drank 16 ounces of water towards a 64-ounce daily goal."* -> Generates a **Hydration Tracker** app with a progress bar and quick `+8 oz` / `+16 oz` buttons.
