# Firmware

The shell that ships on the XIAO ESP32-S3 Plus. It paints JSON from `contract/`. It does not compile generated code.

Build with PlatformIO from this folder:

```bash
pio run -t upload
pio device monitor
```

`src/main.cpp` prints the boot test, then `src/eink.cpp` copies the simulator's agent home pixels onto the 6382. Those pixels live in `src/sim_home.h`. It prints `eink: refresh` with how long the panel stayed busy. Expect about 10–15 seconds. To put a different sim screen on the board, set the waveform to Instant, download the PNG, and run `python3 sim/pack_frame.py that.png`. After that, `src/wifi_link.cpp` joins the network. The `ufdevice` name and password are in `src/wifi_link.h`. `src/ai.cpp` is the Vertex client for a later shell call: `aiAsk(text, registryJson, turnJson)` returns the inner propose, mutate, or say object. The key is `GEMINI_API_KEY` in `src/gemini_key.h`, copied from the repo-root `.env`. That header stays untracked. Boot does not call the model.

## Own this

- Display driver for the Adafruit 6382 (SSD1683, 400×300, black / white / red) on the 4224 Friend. `src/eink.cpp` is the first paint
- Thumbwheel actions from `contract/modules/`
- LittleFS store for the registry
- `aiAsk` in `src/ai.cpp`. Send `text` until the mic path exists
- One paint per result. Input can queue while the panel is busy

## Leave to bring-up

Pin proofs and the measured refresh time live in [`bringup/`](bringup/). Copy a working display init into the shell once a full red/black/white frame has been timed.

## Pins

Use the pad names in [`context/hardware.md`](../context/hardware.md). `D8` is GPIO7.

Board settings in `platformio.ini` assume the Plus: 16MB flash and OPI PSRAM. If the first upload fails or PSRAM reports 0, that file is the place to fix it.
