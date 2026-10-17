# Board bring-up

Prove the parts, then hand a known-good init to the shell. Keep sketches in this folder so they stay out of `src/main.cpp`.

Do these in order. Stop on the first one that fails.

1. **Boot.** Flash `firmware/` and read `omni shell boot` on USB serial.
2. **Display.** Full-frame bars: white, black, red. Record how many seconds `BUSY` stays high. The plan assumes 10–15 seconds for this tri-color glass. Write the number you measure at the top of this file.
3. **Wheel.** Log up, down, and center on `D4`, `D3`, and `D19`. Inputs are active-low to ground.
4. **Mic.** Record one second of I2S from `D7` / `D6` / `D5` and confirm the samples are not stuck at zero. Leave logs on USB. Those pads are the default UART.
5. **Wi-Fi.** Join a phone hotspot and POST `contract/fixtures/requests/text-milk.json` to the stub. Print the JSON body.

Pins and the strapping-pin caution (reset on `D2`, MOSI on `D10`) are in [`context/hardware.md`](../../context/hardware.md).

## Measured refresh

_Not measured yet._
