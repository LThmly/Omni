# Firmware

The shell that ships on the XIAO ESP32-S3 Plus. It paints JSON from `contract/`. It does not compile generated code.

Build with PlatformIO from this folder:

```bash
pio run -t upload
pio device monitor
```

`src/main.cpp` only prints a boot line over USB serial. First job after that print works: load `contract/fixtures/apps/shopping.json` from flash and draw it.

## Own this

- Display driver for the Adafruit 6382 (SSD1683, 400×300, black / white / red) on the 4224 Friend
- Thumbwheel actions from `contract/modules/`
- LittleFS store for the registry
- `POST /v1/turn` client. Dev host is the stub on port 8787. Send `text` until the mic path exists
- One paint per result. Input can queue while the panel is busy

## Leave to bring-up

Pin proofs and the measured refresh time live in [`bringup/`](bringup/). Copy a working display init into the shell once a full red/black/white frame has been timed.

## Pins

Use the pad names in [`context/hardware.md`](../context/hardware.md). `D8` is GPIO7.

Board settings in `platformio.ini` assume the Plus: 16MB flash and OPI PSRAM. If the first upload fails or PSRAM reports 0, that file is the place to fix it.
