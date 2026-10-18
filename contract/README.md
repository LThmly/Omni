# Omni response contract v2

Gemini, the local simulator, and the Pi share one data contract. Gemini returns JSON data; it never supplies executable code, URLs to run, custom widget types, or pixel coordinates.

## Intent and operation

Every response has the same envelope: `{"turn": {...}}`. The turn requires `schema_version: 2`, `intent`, `op`, and a nonempty plain-text `say` response.

| User intent | Operation | Required payload | Device behavior |
| --- | --- | --- | --- |
| `message` | `say` | `say` only | Show the answer; leave apps unchanged |
| `create_app` | `propose` | Complete `app` | Validate, save, and select the generated app |
| `update_app` | `mutate` | Existing `app_id`, approved `actions` | Apply the complete batch atomically |
| `navigate` | `navigate` | `destination`, `app_id` | Open the requested existing page |

An app/navigation request that needs clarification or cannot be fulfilled uses `op: "say"` while retaining its original `intent`. A question *about* an app is `message`; merely mentioning a noun does not create an app. Intent classification is performed by Gemini's system instructions and schema, not a keyword filter in the real backend. The offline preview has limited command matching.

Navigation destinations are `agent`, `apps` (the wheel), `settings`, `notes`, `clock`, `calculator`, or `app`. Named pages require `app_id: null`. `destination: "app"` requires the ID of an existing generated app. Unknown pages/IDs are rejected, never created.

```json
{
  "turn": {
    "schema_version": 2,
    "intent": "navigate",
    "op": "navigate",
    "say": "Opening settings.",
    "destination": "settings",
    "app_id": null
  }
}
```

“Take me to the main agent view” uses `destination: "agent"`. “How do I open settings?” is a message, and “Create a settings shortcut app” is an app request.

## Predefined components and interactions

New generated apps have `module: "composed"`, plus `id`, `title`, `state.fields`, `components`, and `actions`. The device arranges components in array order in one scrolling column. The renderer owns typography, colors, sizing, touch handling, and the keyboard.

| Component | Binding / behavior |
| --- | --- |
| `text` | Literal `text`, or a text-field `bind`; literal text uses `bind: null` |
| `number` | Number-field `bind`, static `label` and `unit` |
| `progress` | Number-field `bind`, positive `goal`, static `label` and `unit` |
| `toggle` | Boolean-field `bind`; a tap toggles it |
| `list` | Items-field `bind`; a row tap toggles its `checked` value |
| `input` | Text-field `bind`; editing uses the local keyboard |
| `button` | Static `label` and an `action` ID referencing an approved app action |

State fields have unique IDs and explicit types: `text`, `number`, `boolean`, or `items`. Number fields declare `min` and `max`. Items contain only `id`, `label`, and `checked`. Bindings must point to existing fields of the correct type.

| Approved action | Fields | Effect |
| --- | --- | --- |
| `set` | `target`, `value` | Set a value of the target field's type |
| `increment` | `target`, `amount` | Change a number, clamped to its bounds |
| `toggle` | `target` | Flip a boolean |
| `append` | `target`, `source` | Read a text field, append an item, then clear the source |
| `clear` | `target` | Empty a text field or items list |
| `remove_checked` | `target` | Remove checked items from a list |

App actions also have an `id`; operations in `mutate.actions` omit it. This is the interaction graph: components reference fields, buttons reference actions, and actions change fields that other components display. A note/list app can bind an input to `entry`, an Add button to an append action (`source: entry`, `target: items`), and a list to `items`. See [the complete shopping example](fixtures/v2/create-shopping.json).

## Enforcement and persistence

- All objects reject extra properties. Unsupported widgets/actions, missing references, duplicate IDs, mismatched types, non-finite numbers, reserved app IDs, and unknown update/navigation targets are rejected.
- Apps are limited to 24 components, 32 fields, 32 actions, and 100 items per list. IDs use lowercase snake_case (32 characters maximum); titles are at most 16 characters. Text fields allow 2,000 characters; item labels allow 120.
- `turn.gemini.json` constrains Gemini's closed object structure, tags, and value types. Vertex rejected this union with every range/size constraint included, so those bounds are checked with the complete schema locally.
- `turn.strict.json` validates the complete wrapped response; `turn.schema.json` validates the inner turn; `app.schema.json` validates saved generated apps. `runtime.py` additionally checks cross-references, type compatibility, numeric bounds, and registry IDs.
- Both the cloud client and pygame controller validate before changing apps. A bad response fails visibly; it never falls back to a fake successful app. Mutations are validated and applied on a copy before committing the whole batch.
- The latest validated turn, including its `intent`, is persisted as `last_turn` alongside the device registry. Transcripts remain internal; the main screen displays only `say`.
- The original template fixtures remain for compatibility tests. Existing generated template apps migrate to component apps with a `registry.pre-components.json` backup. Default Omni, Settings, Notes, Clock, and Calculator remain device-owned.

## Files and verification

`build_schema.py` is the schema source. Regenerate with `python3 contract/build_schema.py`; check generated files with `python3 contract/build_schema.py --check`. `modules/composed.json` lists the catalog. `fixtures/v2/` contains validated app, message, mutation, and navigation examples. Original `fixtures/apps/` and `fixtures/turns/` are legacy compatibility data, not the current Gemini output contract.

Install `cloud/requirements.txt` for validation (`sim/requirements.txt` includes it). Run cloud/contract tests with `python3 -m unittest discover -s cloud -p 'test_*.py'`, and controller/renderer tests with `python3 -m unittest discover -s firmware -p 'test_*.py'`.

See the [generated-app layout and workflow guide](../docs/GENERATED_APPS.md) for real app pages, consistent controls, numeric forms, editable collections with undo, atomic action batches, calculations, and change handlers. Existing v2 apps remain compatible.

Playable choice games use the predefined `choice_game` component and atomic `play_choice` operation. A curated icon catalog, validated dominance rules, independent random opponent, automatic scoring, and a local reveal animation replace fake numeric-move scorecards. See [the RPS reference](fixtures/v2/rock-paper-scissors.json) and the workflow guide for the six typed bindings and supported choices.
