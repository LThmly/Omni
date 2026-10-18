# Hardware Context: Parts, Wiring & Pinout

## Parts List

- **Microcontroller:** Seeed Studio XIAO ESP32S3 Plus (16MB Flash, 8MB PSRAM, Wi-Fi 2.4GHz)
- **Display Panel:** Adafruit 6382 (4.2" Tri-Color E-Ink Display – 400×300 Black/White/Red SSD1683)
- **Display Driver:** Adafruit 4224 (eInk Breakout Friend)
- **Microphone:** Adafruit 6049 (I2S MEMS Microphone Breakout – ICS-43434)
- **Navigation Switch:** Same Sky TS43-135255-10-BK-200-SMT-TR (Up / Down / Push Thumbwheel Navigation Switch)
- **Battery:** 3.7V 1200mAh LiPo Pouch Cell (603450)
- **Power Switch:** SPDT Slide Switch (in-line on battery positive line)
- **Wiring:** 24–28 AWG harvested from USB cable

---

## Wiring & Pinout List

Wire to the silkscreen pad (`D0`, `D1`, `D2`, `D3`, `D4`, `D5`, `D6`, `D7`, `D8`, `D9`, `D10`, `D19`).
The chip GPIO is in parentheses and does not match the pad index (e.g., `D8` is GPIO7). Sources: the [Seeed pin table](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) and the `XIAO_ESP32S3_Plus` Arduino variant.

### Power Subsystem
- **Battery Red Lead (+):** Connect to SPDT Switch Center Pin
- **SPDT Switch Outer Pin:** Connect to XIAO `BAT+` pad (underside pad)
- **Battery Black Lead (-):** Connect to XIAO `BAT-` / `GND` pad (underside pad)

### Adafruit 4224 (eInk Friend) -> XIAO ESP32S3 Plus
- **VIN** -> `3V3`
- **GND** -> `GND`
- **SCK** -> `D8` (GPIO7)
- **MOSI** -> `D10` (GPIO9). *Note: GPIO9 is a strapping pin; confirm the Friend does not hold it during boot.*
- **ECS (Display CS)** -> `D0` (GPIO1)
- **DC (Data/Command)** -> `D1` (GPIO2)
- **RST (Reset)** -> `D2` (GPIO3). *Note: GPIO3 is a strapping pin; same boot caution as MOSI.*
- **BUSY** -> `D9` (GPIO8). *Note: This pad is also the hardware MISO pin. Using it as a GPIO input is fine because the panel is not read over SPI.*
- **MISO & SRCS:** Leave disconnected. The panel is write-only SPI, and the Friend's SD card is unused. The 8MB PSRAM is on the XIAO itself and does not use these pins.

### Adafruit 6049 (I2S Microphone) -> XIAO ESP32S3 Plus
- **3V3** -> `3V3` (shared with eInk Friend)
- **GND** -> `GND` (shared with system ground)
- **DOUT (Data Out)** -> `D7` (GPIO44). *Note: Default UART RX; logs stay on native USB, so mic claims D7.*
- **BCLK (Bit Clock)** -> `D6` (GPIO43). *Note: Default UART TX; logs stay on native USB, so mic claims D6.*
- **LRCL / WS (Word Select)** -> `D5` (GPIO6)
- **SEL:** Tie to `GND` (Left audio channel)

### Same Sky TS43 Thumbwheel Navigation Switch -> XIAO ESP32S3 Plus
The navigation button provides 3-way tactile control: Up rotation/detent, Down rotation/detent, and Center Push with short-click and long-press (Push-to-Talk).
- **Common Pin:** Connect to `GND` (all switch inputs configured with `INPUT_PULLUP`)
- **Up Contact:** Connect to `D4` (GPIO5)
- **Down Contact:** Connect to `D3` (GPIO4)
- **Center Push Contact:** Connect to underside / edge pad `D19` (GPIO11)

#### Navigation Input Behavior
| Switch Input | Gesture | Action |
| :--- | :--- | :--- |
| **Up** | Detent Click | Move selection up on launcher; scroll items up in checklist; switch active team in scoreboard; cycle buttons in progress tracker |
| **Down** | Detent Click | Move selection down on launcher; scroll items down in checklist; switch active team in scoreboard; cycle buttons in progress tracker |
| **Center Push** | Short Press (< 400ms) | Select/open highlighted app; toggle checkbox `[ ]` <-> `[X]`; increment score (+1); trigger button action; confirm proposal |
| **Center Push** | Long Press / Hold (>= 500ms) | **Push-to-Talk (PTT):** Hold to record microphone audio / activate Omni agent; release to dispatch turn request |
