# Omni Architecture (Hackathon)

## Decision

The device does not compile code, and a computer does not push firmware during the demo.

Firmware is a fixed shell, flashed once from a laptop before anyone is watching. After that the device is standalone: battery, Wi-Fi, microphone, thumbwheel, e-ink. The only thing that changes at runtime is a JSON document.

Three programs share that document:


| Runtime           | Job                                                                                     | When it runs                         |
| ----------------- | --------------------------------------------------------------------------------------- | ------------------------------------ |
| Browser simulator | Render the same JSON at 400×300 in black, white, and red. Pretend to be the thumbwheel. | All day, no board required           |
| ESP32 shell       | Capture audio, store apps, apply local input, paint the panel                           | Demo, and occasional hardware checks |
| Cloud agent       | Speech-to-text, then one structured action against the module catalog                   | Whenever someone talks               |


The laptop is a build machine. It is not on stage.

## Why the device cannot compile its own apps

The XIAO ESP32-S3 Plus cannot host a C++ compiler, and it should not interpret generated code either. A generated app that is actually a program will miss the e-ink limits, miss the thumbwheel, and fail live. Flashing a new binary for every prompt also puts a computer back in the demo.

So the model never writes C++, JavaScript, HTML, or an arbitrary API call. It picks a module the firmware already knows how to draw, and it fills in that module's fields.

## What crosses the network

One endpoint, baked into the firmware. Something like `POST /v1/turn` with the wav and the current app registry. The response is one of three actions:

- `propose` — a new app: module name, title, initial state
- `mutate` — an operation on an app that already exists (`toggle`, `append`, `inc`, `add`)
- `say` — a short line for the agent card, when no app should change

The server checks the JSON against the catalog before the device sees it. If the model returns something outside the catalog, retry once, then `say` a failure. The device does not try to repair model output.

Generated apps do not get their own API keys or HTTP. The three demo scenarios (shopping list, scoreboard, hydration) are local state only. If a later module needs outside data, the cloud fills that state in before it sends the document. The device still just renders.

## What stays on the device

Thumbwheel input never waits on the network.

Each module declares a few operations the shell can apply by itself: scroll, toggle a check, increment a score, add a fixed step toward a goal. Those write LittleFS (or PSRAM with a flush) and then paint. Voice still goes to the cloud, because it needs language, but it comes back as the same operations. "Check off milk" by voice and a center-press on Milk are one code path.

If Wi-Fi dies mid-demo, apps that already exist keep working. Only creation and voice edits need the network. Seed one app before the talk so there is something to scroll even if the hotspot drops.

## Demo without a computer on the table

1. Flash the shell once, offstage. The API URL is already in the binary.
2. Device joins a phone hotspot. Venue Wi-Fi is the usual failure.
3. The agent is a small hosted HTTPS service. It can be a machine in a bag. It is not a laptop the presenter drives.
4. Hold the wheel, talk, let go. One screen update when the result is ready.
5. Scroll and check items on the device alone.

Push-to-talk audio is a wav upload. Do not put speech-to-text or an LLM on the ESP32 for this demo.

## The display is the constraint

The panel is a 4.2" 400×300 SSD1683 tri-color (Adafruit 6382). A comparable SSD1683 black/white/red glass is specified around **10 seconds** fast refresh and **15 seconds** standard. Plan for that. The ~0.5 second partial refresh published for SSD1683 is a different, black-and-white panel. Do not budget the demo on it.

Consequences:

- A red selection that repaints on every thumbwheel detent will spend the demo waiting on the panel.
- Agent states (listening, thinking, responding) cannot each be their own refresh. Four paints is most of a minute.
- Listening is the held wheel, not a screen mode. Paint once, when the result is ready.
- Red is for rare marks: recording already in progress is too late to paint, so use red for the selected row at rest, alerts, and the confirm option. Do not animate with it.
- The shell coalesces input. Several detents become one paint.

The simulator needs a refresh lock, defaulting to about 12 seconds, with a key to skip it. Otherwise the UI will be designed for a monitor and feel broken on the board.

Pixels are only black, white, or red. They do not mix.

## Modules

Yes. Build a small catalog. The model pulls from it. It does not invent widgets.

Hackathon catalog, which covers all three scripts in the overview:


| Module       | Draws                     | Local operations                       | Demo line                                       |
| ------------ | ------------------------- | -------------------------------------- | ----------------------------------------------- |
| `checklist`  | Title, rows, a check mark | `scroll`, `toggle`, `append`, `remove` | "Add milk to my shopping list."                 |
| `scoreboard` | Two names, two numbers    | `scroll`, `inc`, `dec`                 | "Keep score for ping pong between me and Alex." |
| `progress`   | Label, value, goal, a bar | `add` by a fixed step                  | "Log 16 ounces toward 64."                      |
| `key_value`  | Read-only rows            | `scroll`                               | Spare. Do not demo unless the others are done.  |


Shell screens are not modules and are not generated: the home dock, the agent line, and the yes/no confirm. "Want me to make a shopping list?" is the shell, drawn from a `propose` action.

A module instance looks like this:

```json
{
  "id": "shopping",
  "module": "checklist",
  "title": "Shopping",
  "state": {
    "items": [{ "label": "Milk", "checked": false }]
  }
}
```

Voice routing for the demo is the same model call, with the registry in the prompt. A second intent classifier is extra machinery. The second shopping prompt should return `mutate` on `shopping`, not a new app.

## Simulator

Build a thin browser page that consumes the JSON above. That is the development loop.

- Canvas is 400×300, scaled up with nearest-neighbor, three colors only.
- Keys stand in for the wheel: up, down, center, hold-to-talk.
- In the browser, hold-to-talk can be a text box. On device it is the wav.
- Refresh lock defaults on, so layout decisions meet the panel's speed.
- The same fixture JSON files load in the browser and on the board.

[eink-simulator](https://github.com/slavik0329/eink-simulator) is a useful reference for Adafruit GFX font metrics. It is a drawing sandbox, not an Omni runtime. [Velxio](https://velxio.dev/v3/) can simulate an SSD168x tri-color panel down at SPI, which is more hardware than this week needs. Use the JSON page for UI work. Touch the board to prove paint time, pin wiring, and the microphone.

## Cut line

In scope: the shell, the three modules, one cloud turn endpoint, the browser simulator, local thumbwheel edits.

Out of scope: on-device compilation, on-device speech-to-text, an on-device model, generated code, per-app HTTP, an app store, grayscale, and partial-refresh research. Partial refresh is a gift if someone proves it on this exact glass. It is not the plan.

## Repo

Lanes and how to start them are in the root `README.md`. `contract/` is the JSON firmware, the simulator, and the cloud share. `firmware/bringup/` is where a measured refresh time gets written down.

## Hardware notes that affect this

Pin corrections live in `hardware.md`. Two of them matter here:

- Silkscreen pads `D0`–`D10` are not GPIO 0–10. Wiring by the parenthetical GPIO numbers in the old doc would miss the pads.
- `D6` and `D7` are the default UART pins (GPIO43, GPIO44). They are fine for the I2S mic because logs go over native USB. Do not also bit-bang serial on them.

