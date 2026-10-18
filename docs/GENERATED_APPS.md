# Generated app layout and workflows

Generated apps use the shared pygame app shell on desktop and Pi. The shell owns margins, typography, touch targets, scrolling, navigation, and action placement. Gemini describes state and interactions; it cannot generate executable code or screen coordinates.

## Layout

- A fixed title and back control remain accessible while content scrolls.
- Optional `pages` provide up to four real app sections. Each page has `id`, `title`, and an ordered list of component IDs. Existing apps without pages continue to work.
- Components share 24-pixel margins, 16-pixel spacing, rounded surfaces, readable sans-serif type, and consistent light/dark colors. Text and list rows wrap instead of silently discarding long content.
- The last one or two action buttons on a page stay at the bottom. A trailing text input on collection pages stays with those actions. Ordinary form fields remain grouped in the content.
- Destructive collection actions use secondary styling. Incomplete append/save operations and division by zero are disabled where detectable, and the runtime also rejects invalid operations atomically.
- Pages remember their scroll positions during the session, scroll to the actual end of the content, and display a scroll indicator. Wrapped text measurements are cached and offscreen list rows are not drawn.
- List and record rows have distinct completion, edit, and removal controls. Removing an entry offers a four-second, one-step undo above the action area. Numeric fields use a decimal/negative-capable touch keypad; text keyboards include punctuation and Clear.

## Shared visual assets and app logos

The bundled [offline catalog](../assets/icons/README.md) contains **1,903 canonical icons/illustrations**, plus compatible aliases. This is shared infrastructure for every generated app, not a per-game art system. `app.icon` controls the launcher and header symbol; tap the header symbol to search and select another logo, or select Auto. Existing apps get an inferred logo without rewriting their data.

Every component accepts optional `icon`. The renderer uses these on text/hero cards, metric and form labels, toggles, collection headings, and action buttons. Collection entries accept optional `icon`, displayed in selectable options, list rows, stat cards, and illustrated decks. Existing controls retain accessible hit targets and their action bindings. Common older metrics/actions get sensible default symbols when no icon is declared.

Standalone artwork uses `{id, type:'illustration', icon:'basketball', label:'Your practice session', size:'medium'}`. Sizes are small/medium/large (64/96/144 pixels). Assets are monochrome and adapt to dark/light and selected controls. Use one relevant visual anchor and a consistent hierarchy rather than repeating large decoration or making content scroll needlessly. Icons improve recognition and identity; they do not imply functionality that the runtime cannot implement.

All IDs are semantically validated across app/component/item/game references, including atomic mutations. Unknown names, URLs, and paths fail validation. The generation client sends at most 64 relevant assets with each request and asks Gemini to choose a topic-specific logo, meaningful artwork, and restrained component icons. The source pack and rendered surfaces load on demand with bounded caches, so a thousand-icon catalog does not require preloading a thousand images or parsing SVG on the Pi.

## Contract additions (backward-compatible v2)

`number_input` binds to a bounded number field and commits a validated value on Done. Text input now also commits through the atomic operations path on Done. Cancelled edits do not alter app state.

New operations:

| Operation | Fields | Behavior |
| --- | --- | --- |
| `calculate` | `target`, `operator`, `left`, `right` | Writes a bounded numeric result. Operators are add/subtract/multiply/divide; operands are `{field: id}` or `{literal: number}`. No expression/code evaluation. |
| `append_record` | `target`, `source`, `amount` | Reads text source plus number amount; adds a `label: number` item and clears the text source. |
| `sum_records` | `target`, `source` | Sums numeric values from an items source in `label: number` format. Invalid records produce an error. |
| `batch` | `steps` | Executes 1–8 non-batch operations atomically. No nested batches. |

A bound component can optionally declare `on_change: action_id`. After an edit or complete batch changes its field, that action runs once, as part of the same atomic transaction. Identical handlers are deduplicated; multiple handlers run in action-ID order. Changes made by handlers do not recursively trigger another round. Put dependent calculations into one handler batch in the required order.

Page references, change-handler IDs, operation types, bounds, operands, and data limits are validated before application. Failures leave the original state intact. Existing seven-component apps and the previously expanded component catalog remain accepted; the layout layer consolidates their controls into consistent visual families. `xy_pad` now presents a truthful bounded slider rather than implying two state dimensions.

## Complete example

### Playable choice games

`choice_game` is a complete native game surface, rather than a composition of editable counters. It renders cached vector hand illustrations, large move buttons, a matchup arena, a clear result, and a compact score strip in both themes. A 620 ms throw/reveal animation blocks additional move taps; reduced motion shows the result immediately. Back remains accessible. RPS fits on one screen without scrolling, with a secondary, confirmation-protected New match action.

The component binds to six distinct typed fields: `bind` is the text outcome (`''`, `win`, `loss`, `draw`); `player` and `opponent` are text choice IDs; `wins`, `losses`, and `draws` are bounded, nonnegative integer scores. Initially moves/result are empty and scores are zero. Its 3–5 `choices` declare `id`, `label`, a curated `icon` (`rock`, `paper`, `scissors`, `flame`, `water`, `leaf`), and `beats` IDs. Every pair must have exactly one winner. Standard RPS rules are enforced for rock/paper/scissors IDs. State types, rule references, score bounds, and completed-round consistency are validated.

The approved `play_choice` operation uses the same bindings/rules plus `target` (result field) and `choice` (player's move). It independently samples the opponent uniformly, resolves the winner, and increments exactly one score atomically. Moves, outcome, and scores persist together; no network request is needed to play. At the score limit it rejects the round with a New match instruction instead of silently losing scores. Components call this operation themselves; the model does not need to invent Play buttons, numeric move codes, randomizers, or manually edited scores. This supports declarative dominance-rule games, not arbitrary game code or unimplemented modes such as difficulty/best-of matches.

[`rock-paper-scissors.json`](../contract/fixtures/v2/rock-paper-scissors.json) is the curated reference. Ask Gemini 3.1 Pro “Create a rock paper scissors game” or use `--backend demo` with the same request. New generation rules require the playable component and forbid a scorekeeping substitute. Existing saved scorecards retain their original schema until explicitly replaced/regenerated; schema expansion alone does not rewrite user apps. Seven game regression tests cover all nine outcomes, custom rules, offline generation, invalid rules/bindings/assets, rollback, score limits, touch drift, duplicate taps, reduced motion, reset, persistence, and theme-aware asset caching.

[`contract/fixtures/v2/expense-log.json`](../contract/fixtures/v2/expense-log.json) demonstrates Overview, Add, History, and Setup pages. Its Save action appends a record and resets the amount. The history change handler sums the records and calculates remaining budget. Renaming a record, deleting it, undoing its removal, or changing the budget updates dependent totals as well.

Use `label: number` when editing a financial record; invalid values are rejected and the edit remains open with an explanation. This format is intentionally explicit within the current typed-items contract; it is not an arbitrary database or an external finance integration.

Try in the simulator:

```sh
sh sim/run.sh --backend gemini
```

Then type/say “Create an expense tracker with a budget and editable history”, “Build a workout log with a rest timer”, or “Create a project checklist”. The offline demo also supports an expense/budget template:

```sh
sh sim/run.sh --backend demo
```

Ask “Create an expense tracker”. Generated apps appear selected on the wheel after the acknowledgment. No example is installed into the user's live profile automatically.

## Verification

`firmware/test_generated_apps.py` checks complete expense-save workflows, pages, persistence, atomic rollback, numeric validation, list editing/deletion/undo, dependent calculations, timer completion, slider dragging, numeric keypad input, and rendering every registered component in both themes. Existing ASR, touch-drift, local command, transition, and response-before-action tests also continue to apply.

During implementation, three actual Gemini outputs (expense tracker, workout log, project checklist) validated with the expanded schema, rendered successfully, and had their registered actions exercised on copies of their state. Model quality still varies; keep the generation instructions and curated example aligned with actual renderer/runtime capabilities.

Timers save remaining seconds while running and continue updating if another page is selected. Running status is session-local; restarting the app restores the last saved remaining value, not an OS alarm. On-change handlers are declared dependencies, not a general reactive programming engine. No background notifications, network accounts, or arbitrary code execution are implied.
