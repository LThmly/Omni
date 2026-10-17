# Phone

The phone is a pygame window. From the repo root:

```bash
python3 firmware/shell.py
```

That opens the 480×800 phone upright. On the Pi, `firmware/demo.sh` opens the same window fullscreen and turns it 90° onto the 800×480 glass. A click here is a finger on the XPT2046.

Start the stub in another terminal so List, Score, Water, and the talk bar get a reply:

```bash
python3 cloud/stub_server.py
```

`POST http://127.0.0.1:8787/v1/turn` with `{ "text", "registry" }`. `propose` draws the confirm card. `mutate` updates the app and opens it.

The five-arrow mark is drawn in `firmware/phone.py`. The Neuropolitical wordmark is `sim/neuropolitical.ttf`. Layout spacing (`margin`, `header_h`, `row_h`, `bar_h`) comes from `contract/modules/`.

Apps already on the device are stored in `~/.omni/registry.json`.
