# Device shell

The phone that opens on the 5" XPT2046 panel. It paints JSON from `contract/`. It does not compile generated code. A finger is the input.

The page lives in [`sim/`](../sim/). This folder is how that page gets onto the Pi and stays there. A laptop shows the same phone upright. The Pi turns it 90° so it fills the glass.

## Run it on a laptop

```bash
python3 firmware/shell.py
```

Open `http://127.0.0.1:8080/sim/`.

## Demo on the Pi

From a terminal on the Pi desktop:

```bash
sh firmware/demo.sh
```

The first run writes the XPT2046 touchscreen overlay and the 800×480 mode, then reboots. After you log in, the phone opens on the glass and stays there. A later run skips the reboot and opens it immediately.

What you can press:

- A row opens that app. On Shopping, a tap checks an item. On Ping pong, `+` and `−` change the score. On Water, `+8 oz` and `+16 oz` move the bar.
- **List**, **Score**, and **Water** on the home screen send those three demo lines. List and Score and Water each pop a confirm card, or they edit an app that is already there. **Yes, create it** and **Cancel** are fingers, not the network.
- Hold the talk bar. It sends “Add milk to my shopping list.” The microphone is not connected.

Quit with Ctrl+Shift+Q, or `python3 firmware/shell.py --stop`. The next login opens the demo again.

## Own this

- `demo.sh` writes the touchscreen overlay, registers login, and opens the phone
- `shell.py` serves the phone and keeps the fullscreen window up
- The portrait UI in `sim/shell.css` and `sim/shell.js`, including the arrow mark and Neuropolitical wordmark
- Push-to-talk is on the phone. The simulator sends the text box. Microphone capture is the next piece of device work

## Mount

Stand the stack in portrait, right edge up. Touch setup, quit keys, and the `--turn left` switch are in [`bringup/`](bringup/).
