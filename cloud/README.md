# Cloud

`POST /v1/turn` turns an utterance plus the device registry into one response from `contract/turn.schema.json`.

## Stub, no key

```bash
python3 cloud/stub_server.py
```

Port 8787. It matches keywords and returns files in `contract/fixtures/turns/`. `sh sim/run.sh --live` posts here.

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

`cloud/try_turn.py` calls Vertex express at `aiplatform.googleapis.com` with `contract/turn.gemini.json` as the generation schema (with the full `turn.strict.json` validated locally). This key is bound to the Agent Platform service account, so it cannot call `generativelanguage.googleapis.com`. The reply is one `propose`, `mutate`, `say`, or `navigate` object.

Put `GEMINI_API_KEY` in an untracked `.env` at the repo root. See `.env.example`. The default app-generation model is `gemini-3.1-pro-preview` (Gemini 3.1 Pro); `GEMINI_MODEL` overrides it. Existing `.env` files must be updated when switching models. Earlier testing used `gemini-3.8-flash`.

```bash
python3 cloud/try_turn.py "Add milk to my shopping list."
python3 cloud/try_turn.py "Add coffee" --registry contract/fixtures/registry.json
```

The schema root is `{"turn": ...}`. The script prints the inner object, which matches `contract/turn.schema.json`. Import `ask()` for the same call. A reply that cannot be used raises `TurnError` instead of exiting the process. The pygame shell calls this client directly with `--backend gemini` and applies the returned turn to its UI. `--backend stub` keeps the HTTP path available.

Vosk speech recognition runs locally on the device. In Vosk mode Gemini receives finalized text; recorded `wav_base64` requests remain supported for the non-Vosk recording path. Without a key, the stub matches text keywords and can optionally transcribe audio if its speech-recognition dependency is available.

## Current strict contract (v2)

See [contract/README.md](../contract/README.md) for the authoritative response contract. Gemini returns only `{"turn": {...}}`, with a version, intent (`message`, `create_app`, `update_app`, `navigate`), operation, and clear user-facing `say`. Apps are compositions of fixed components bound to typed state and approved actions. Navigation opens named device pages or existing app IDs. The client rejects incomplete, malformed, or semantically invalid responses; errors do not silently become preview apps.

Install validation with `python3 -m pip install -r cloud/requirements.txt`. The model-facing structural schema is `turn.gemini.json`; the full bounded schema and interaction graph are enforced locally. The controller validates again, applies the result, and persists its classified turn. The Pi deployer installs these validation requirements before its tests.
