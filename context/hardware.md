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

Wire to the silkscreen pad (`D8`, `D10`, …). The chip GPIO is in parentheses and does not match the pad index: `D8` is GPIO7. Sources: the [Seeed pin table](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) and the `XIAO_ESP32S3_Plus` Arduino variant.

### Power Subsystem
- **Battery Red Lead (+):** Connect to SPDT Switch Center Pin
- **SPDT Switch Outer Pin:** Connect to XIAO `BAT+` pad (underside pad)
- **Battery Black Lead (-):** Connect to XIAO `BAT-` / `GND` pad (underside pad)

### Adafruit 4224 (eInk Friend) -> XIAO ESP32S3 Plus
- **VIN** -> `3V3`
- **GND** -> `GND`
- **SCK** -> `D8` (GPIO7)
- **MOSI** -> `D10` (GPIO9). GPIO9 is a strapping pin; confirm the Friend does not hold it during boot.
- **ECS (Display CS)** -> `D0` (GPIO1)
- **DC (Data/Command)** -> `D1` (GPIO2)
- **RST (Reset)** -> `D2` (GPIO3). GPIO3 is a strapping pin; same boot caution as MOSI.
- **BUSY** -> `D9` (GPIO8). This pad is also the hardware MISO pin. Using it as a GPIO input is fine because the panel is not read.
- **MISO & SRCS:** Leave disconnected. The panel is write-only SPI, and the Friend's SD card is unused. The 8MB PSRAM is on the XIAO itself and does not use these pins.

### Adafruit 6049 (I2S Microphone) -> XIAO ESP32S3 Plus
- **3V3** -> `3V3` (shared with eInk Friend)
- **GND** -> `GND` (shared with system ground)
- **DOUT (Data Out)** -> `D7` (GPIO44). This pad is also the default UART RX. Logs stay on native USB, so the mic can take it.
- **BCLK (Bit Clock)** -> `D6` (GPIO43). Default UART TX. Same note as DOUT.
- **LRCL / WS (Word Select)** -> `D5` (GPIO6)
- **SEL:** Tie to `GND` (Left audio channel)

### Same Sky TS43 Thumbwheel -> XIAO ESP32S3 Plus
- **Common Pin:** Connect to `GND`
- **Up Contact:** Connect to `D4` (GPIO5)
- **Down Contact:** Connect to `D3` (GPIO4). Reset is the neighboring pad, `D2` / GPIO3.
- **Center Push Contact:** Connect to underside / edge pad `D19` (GPIO11)
