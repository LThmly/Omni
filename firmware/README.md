# Omni ESP32-S3 E-Ink Firmware

Dedicated firmware for **Omni**, running standalone on a **Seeed Studio XIAO ESP32S3 Plus** driving an **Adafruit 6382 (4.2" 400×300 Tri-Color Black/White/Red E-Ink display)** via an **Adafruit 4224 Breakout Friend**, an **Adafruit 6049 I2S MEMS microphone**, and a **Same Sky TS43 3-way thumbwheel navigation switch**.

---

## 1. Hardware Pinout & Wiring

Wire to the silkscreen pads of the XIAO ESP32S3 Plus:

| Subsystem | Component Pin | XIAO Silkscreen Pad | ESP32 GPIO | Description |
| :--- | :--- | :--- | :--- | :--- |
| **E-Ink Display** | ECS | `D0` | GPIO1 | Display SPI Chip Select |
| | DC | `D1` | GPIO2 | Data / Command Select |
| | RST | `D2` | GPIO3 | Hardware Reset *(strapping pin)* |
| | SCK | `D8` | GPIO7 | Hardware SPI Clock |
| | BUSY | `D9` | GPIO8 | Panel Busy Status *(input)* |
| | MOSI | `D10` | GPIO9 | Hardware SPI MOSI *(strapping pin)* |
| **Nav Switch** | Common | `GND` | System Ground | Switch Common Pin |
| | Up Contact | `D4` | GPIO5 | Up detent / scroll (`INPUT_PULLUP`) |
| | Down Contact | `D3` | GPIO4 | Down detent / scroll (`INPUT_PULLUP`) |
| | Center Push | `D19` | GPIO11 | Center Push / PTT (`INPUT_PULLUP`) |
| **I2S Microphone** | LRCL / WS | `D5` | GPIO6 | Word Select / Left-Right Clock |
| | BCLK | `D6` | GPIO43 | Bit Clock |
| | DOUT | `D7` | GPIO44 | Serial Data Out |
| | SEL | `GND` | Ground | Select Left Audio Channel |
| **Status LED** | User LED | Onboard | GPIO21 | Heartbeat indicator (active-low) |

---

## 2. Navigation Button Programming & Interaction

The Same Sky TS43 3-way thumbwheel navigation switch provides intuitive single-handed operation:

### Gestures
- **Up / Down Detent:** Momentary contact closure with 25ms hardware debounce.
- **Center Push Short Click (< 450ms):** Selection, toggle, or confirmation action.
- **Center Push Long Press / Hold (>= 450ms):** **Push-to-Talk (PTT)** voice recording. Holding down records from the I2S microphone; releasing dispatches the turn request to the Omni agent.

### Interaction States

| Screen | Thumbwheel Up / Down | Center Short Click | Center Long Press (PTT) |
| :--- | :--- | :--- | :--- |
| **Home (Agent View)** | Cycle through installed apps | Launch highlighted app | Speak to Omni (PTT) |
| **Checklist App** | Move cursor up/down (or to `< Back`) | Toggle `[ ]` / `[X]` (or go Back) | Speak to Omni (PTT) |
| **Scoreboard App** | Switch between teams (or to `< Back`) | Increment score (+1) (or go Back) | Speak to Omni (PTT) |
| **Progress Tracker** | Select quick-add buttons (`+8 oz`, `+16 oz`) | Apply amount (or go Back) | Speak to Omni (PTT) |
| **Proposal Card** | Toggle `[ Yes, create it ]` / `[ Cancel ]` | Confirm choice | Speak to Omni (PTT) |

---

## 3. Build & Flash

### Using PlatformIO (Recommended)

From the project root:

```bash
cd firmware
pio run -t upload
pio device monitor
```

The configuration in `platformio.ini` targets `seeed_xiao_esp32s3` with 16MB Flash and 8MB OPI PSRAM.

### Using Arduino IDE
1. Install **ESP32 by Espressif Systems** via the Boards Manager.
2. Select **XIAO_ESP32S3**.
3. Enable **OPI PSRAM** under Tools -> PSRAM.
4. Set Flash Size to **16MB (128Mb)**.
5. Install required libraries:
   - `ArduinoJson` (v7.x)
   - `Adafruit EPD`
   - `Adafruit GFX Library`
6. Open `firmware/src/main.cpp` and click **Upload**.

---

## 4. Interactive Serial CLI

Connect via Serial monitor at **115200 baud** to monitor device logs or inject navigation events without physical hardware:

| Command | Action |
| :--- | :--- |
| `up` / `u` | Simulate Thumbwheel Up detent |
| `down` / `d` | Simulate Thumbwheel Down detent |
| `click` / `c` | Simulate Center Push short click |
| `ptt` | Simulate PTT Hold Start (starts voice recording) |
| `rel` / `release` | Simulate PTT Hold End (stops recording & sends turn) |
| `turn <text>` | Submit custom utterance (e.g. `turn Add milk to my shopping list`) |
| `home` / `h` | Return to Home screen |
| `demo` | Trigger next offline demonstration turn |
| `status` | Display free heap, PSRAM, active screen, and Wi-Fi IP |
| `reset` | Restore default demonstration apps |

---

## 5. Offline Demonstration Mode

Omni includes an offline demonstration pipeline. If Wi-Fi is unavailable or unconfigured, holding and releasing the Center Push button cycles through the flagship hackathon user journeys:
1. **App Genesis (Shopping List):** Prompts proposal card for a new Shopping List app with Milk. Clicking `[ Yes, create it ]` instantiates and opens it.
2. **State Mutation:** Appends Eggs to the newly created Shopping List.
3. **Scoreboard:** Proposes a Ping Pong Scoreboard with Me and Alex.
4. **Hydration Tracker:** Proposes a water logger tracking towards a 64 oz goal with quick-add buttons.
