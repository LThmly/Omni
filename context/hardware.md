# Hardware Context: Parts, Wiring & Pinout

## Parts List

- **Microcontroller:** Seeed Studio XIAO ESP32S3 Plus
- **Display Panel:** Adafruit 6382 (4.2" Tri-Color E-Ink Display)
- **Display Driver:** Adafruit 4224 (eInk Breakout Friend)
- **Microphone:** Adafruit 6049 (I2S MEMS Microphone Breakout – ICS-43434)
- **Navigation Switch:** Same Sky TS43-135255-10-BK-200-SMT-TR (Up / Down / Push Thumbwheel)
- **Battery:** 3.7V 1200mAh LiPo Pouch Cell (603450)
- **Power Switch:** SPDT Slide Switch (in-line on battery positive line)
- **Wiring:** 24–28 AWG harvested from USB cable

---

## Wiring & Pinout List

### Power Subsystem
- **Battery Red Lead (+):** Connect to SPDT Switch Center Pin
- **SPDT Switch Outer Pin:** Connect to XIAO `BAT+` pad (underside pad)
- **Battery Black Lead (-):** Connect to XIAO `BAT-` / `GND` pad (underside pad)

### Adafruit 4224 (eInk Friend) -> XIAO ESP32S3 Plus
- **VIN** -> `3V3`
- **GND** -> `GND`
- **SCK** -> `D8` (GPIO 8)
- **MOSI** -> `D10` (GPIO 10)
- **ECS (Display CS)** -> `D0` (GPIO 1)
- **DC (Data/Command)** -> `D1` (GPIO 2)
- **RST (Reset)** -> `D2` (GPIO 3)
- **BUSY** -> `D9` (GPIO 9)
- **MISO & SRCS:** Disconnected (uses MCU 8MB internal PSRAM)

### Adafruit 6049 (I2S Microphone) -> XIAO ESP32S3 Plus
- **3V3** -> `3V3` (shared with eInk Friend)
- **GND** -> `GND` (shared with system ground)
- **DOUT (Data Out)** -> `D7` (GPIO 7)
- **BCLK (Bit Clock)** -> `D6` (GPIO 6)
- **LRCL / WS (Word Select)** -> `D5` (GPIO 5)
- **SEL:** Tie to `GND` (Left audio channel)

### Same Sky TS43 Thumbwheel -> XIAO ESP32S3 Plus
- **Common Pin:** Connect to `GND`
- **Up Contact:** Connect to `D4` (GPIO 4)
- **Down Contact:** Connect to `D3` (GPIO 3 / D3 pad)
- **Center Push Contact:** Connect to Underside Pad `GPIO 11` (or `GPIO 12`)
