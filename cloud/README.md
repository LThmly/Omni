# Cloud

`POST /v1/turn` turns an utterance plus the device registry into one response from `contract/turn.schema.json`.

## Stub, no key

```bash
python3 cloud/stub_server.py
```

Port 8787. It matches keywords and returns files in `contract/fixtures/turns/`. The simulator uses this. The board calls the model itself.

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

`cloud/try_turn.py` calls Vertex express at `aiplatform.googleapis.com` with `contract/turn.strict.json` as the response schema. This key is bound to the Agent Platform service account, so it cannot call `generativelanguage.googleapis.com`. The reply is one `propose`, `mutate`, or `say` object.

Put `GEMINI_API_KEY` in an untracked `.env` at the repo root. See `.env.example`. The model that produced a valid shopping turn is `gemini-3.8-flash`.

```bash
python3 cloud/try_turn.py "Add milk to my shopping list."
python3 cloud/try_turn.py "Add coffee" --registry contract/fixtures/registry.json
```

The schema root is `{"turn": ...}`. The script prints the inner object, which matches `contract/turn.schema.json`. `firmware/src/ai.cpp` sends the same request from the board. Its key is the untracked `firmware/src/gemini_key.h`.

Speech-to-text runs here. The device will send `wav_base64`. The stub ignores audio and reads `text`.
