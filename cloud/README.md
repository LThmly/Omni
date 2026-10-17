# Cloud

`POST /v1/turn` turns an utterance plus the device registry into one response from `contract/turn.schema.json`.

## Stub, no key

```bash
python3 cloud/stub_server.py
```

Port 8787. It matches keywords and returns files in `contract/fixtures/turns/`. Firmware and the simulator should integrate against this before anyone wires a model.

| Text contains | Registry | Response |
| :--- | :--- | :--- |
| milk, shopping, list | no checklist yet | `propose-shopping.json` |
| coffee, bread, eggs, add | a checklist exists | `mutate-shopping.json` |
| score, ping, pong | | `propose-scoreboard.json` |
| water, ounce | | `propose-hydration.json` |
| anything else | | `say.json` |

```bash
curl -s localhost:8787/v1/turn \
  -H 'content-type: application/json' \
  -d @contract/fixtures/requests/text-milk.json
```

## Real model

Replace the matcher. Keep the response shape. Validate against `contract/turn.schema.json` before replying. On a bad model payload, retry once, then return `fixtures/turns/say.json`.

Speech-to-text runs here. The device will send `wav_base64`. The stub ignores audio and reads `text`.

Put API keys in a `.env` that stays untracked.
