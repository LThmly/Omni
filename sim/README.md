# Phone simulator

Browser stand-in for the portrait Omni phone. The frame is 480×800, upright. The Pi turns this same page 90° so it fills the 5" 800×480 panel. A mouse click here is a finger on the XPT2046 glass.

From the repo root:

```bash
python3 firmware/shell.py
```

Open `http://127.0.0.1:8080/sim/`. The first visit loads the fixture apps. Taps stay on the device. Speech is the text box, posted to the stub.

```bash
python3 cloud/stub_server.py
```

`POST http://127.0.0.1:8787/v1/turn` with `{ "text", "registry" }`. `propose` draws the confirm card. `mutate` updates the app and opens it.

The home screen uses the five-arrow mark and the Neuropolitical “omni” wordmark from the earlier simulator. `?kiosk=1` hides the studio chrome and turns the phone. That is what `firmware/shell.py --kiosk` opens on the Pi.

Layout spacing (`margin`, `header_h`, `row_h`, `bar_h`) comes from `contract/modules/`. Paint and color live in `shell.css`.
