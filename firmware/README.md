# Device shell

The phone that opens on the 5" XPT2046 panel. It paints JSON from `contract/` with pygame. It does not compile generated code. A finger is the input.

A laptop shows the same phone upright. The Pi turns it 90° so it fills the glass.

## Run it on a laptop

```bash
python3 firmware/shell.py
```

The window is 480×800. Type a request and press Enter. Ctrl+E empties the device, Ctrl+D loads the demo apps again, and Escape goes back. pygame comes from `python3-pygame` on the Pi. On a Mac: `python3 -m venv .venv && .venv/bin/pip install pygame-ce`, then `.venv/bin/python firmware/shell.py`.

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
- `phone.py` draws the phone and keeps the fullscreen window up
- The arrow mark and the Neuropolitical wordmark
- Push-to-talk is on the phone. Until the microphone is connected, holding it sends the milk line. On a laptop, typed text and Enter send a turn instead

## Mount

Stand the stack in portrait, right edge up. Touch setup, quit keys, and the `--turn left` switch are in [`bringup/`](bringup/).
