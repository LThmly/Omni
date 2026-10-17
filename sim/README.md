# E-ink simulator

Browser stand-in for the 400×300 panel. It paints the same JSON as the device.

From the repo root:

```bash
python3 -m http.server 8080
```

Open `http://localhost:8080/sim/`. The page loads `contract/fixtures/apps/shopping.json` and draws it. Wheel keys are wired as a log until the paint path honors them.

## Match the panel

- 400×300, scaled with nearest-neighbor
- Pixels are black, white, or red
- Refresh lock defaults to 12 seconds, with a key that skips it
- Up / down / center, and hold-to-talk as a text box
- Layout numbers come from `contract/modules/*.json`

Talking goes to the stub:

```bash
python3 cloud/stub_server.py
```

`POST http://localhost:8787/v1/turn` with `{ "text", "registry" }`. Apply `propose` and `mutate` to the in-memory registry, then paint once.

Fonts can follow [eink-simulator](https://github.com/slavik0329/eink-simulator) so text metrics are close to Adafruit GFX. The page still has to render Omni apps, not raw draw calls.
