# Contract

This folder is the API between firmware, the simulator, the cloud, and the model. If a field exists only inside one runtime, the other runtimes will drift.

## Files

| Path | What it is |
| :--- | :--- |
| `app.schema.json` | One saved app |
| `turn.schema.json` | `POST /v1/turn` response the device accepts |
| `turn.strict.json` | Same response, shaped so Gemini structured output can fill it |
| `modules/*.json` | State, actions, and pixel layout for each module |
| `fixtures/apps/` | Apps the shell and the simulator can paint with no network |
| `fixtures/turns/` | Responses the cloud stub returns |
| `fixtures/registry.json` | A device that already has a shopping list |
| `fixtures/requests/` | Example turn requests |

## Rules

- Module names are `checklist`, `scoreboard`, `progress`, and `key_value`.
- The app canvas is 480×800, portrait. Layout numbers are CSS pixels, origin top-left. Color lives in `sim/shell.css`.
- `scroll` is device-only. The model does not send it.
- A `mutate` carries an `actions` list so one utterance can append coffee and bread, and the panel paints once.
- `propose.app` is a complete app. The shell stores it when the user confirms.
- Add a fixture in the same change as any new field.

## Request

`POST /v1/turn` with JSON:

```json
{
  "text": "Add milk to my shopping list.",
  "registry": [],
  "focused_app_id": null
}
```

The device sends `wav_base64` instead of `text`. The stub and the simulator use `text`. `registry` is the apps already stored on the device.
