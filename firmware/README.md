# Device shell

The phone that opens on the 5" XPT2046 panel. It paints JSON from `contract/`. It does not compile generated code. A finger is the input.

The page lives in [`sim/`](../sim/). This folder is how that page gets onto the Pi and stays there. A laptop shows the same phone upright. The Pi turns it 90° so it fills the glass.

## Run it on a laptop

```bash
python3 firmware/shell.py
```

Open `http://127.0.0.1:8080/sim/`.

## Leave it running on the Pi

The OS is already on the board. There is no separate image to flash. Once, on the Pi:

```bash
python3 firmware/install.sh
```

Log out and back in. The phone opens over the desktop and stays up. If the window closes, it opens again.

Quit with Ctrl+Shift+Q, or:

```bash
python3 firmware/shell.py --stop
```

To try it before installing:

```bash
python3 firmware/shell.py --kiosk
```

That needs Chromium (`sudo apt install chromium`). The turn stub is separate, on the same machine:

```bash
python3 cloud/stub_server.py
```

## Own this

- `install.sh` registers the app with the Pi desktop session
- `shell.py` serves the phone and keeps the fullscreen window up
- The portrait UI in `sim/shell.css` and `sim/shell.js`, including the arrow mark and Neuropolitical wordmark
- Push-to-talk is on the phone. The simulator sends the text box. Microphone capture is the next piece of device work

## Mount

Stand the stack in portrait, right edge up. Touch setup, quit keys, and the `--turn left` switch are in [`bringup/`](bringup/).
