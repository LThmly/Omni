# Offline icon library

**1,903 canonical assets:** 1,891 Lucide icons and 12 original Omni illustrations. The catalog also accepts 278 legacy/semantic aliases, which are not included in the canonical count. Includes people, animals, objects, sports, nature, food, transport, tools, finance, reading, music, interface symbols, RPS hand gestures, balls, and a runner.

- `catalog.json`: stable IDs, search tags, aliases, source version, and archive checksum.
- `icons.zip`: transparent 144×144 PNG masks for Lucide, loaded individually as needed.
- `LICENSE-LUCIDE.txt`: complete upstream copyright/license notices, retained for redistribution.
- Original illustrations are drawn by `firmware/game_art.py` and `firmware/sport_art.py`.

Source: the official [`lucide-static` npm package](https://www.npmjs.com/package/lucide-static), pinned to **1.59.0**. See [Lucide](https://github.com/lucide-icons/lucide) and the bundled license. PNG masks are rendered from the package's canonical SVG icons. Upstream SVG aliases are matched by identical vector content and resolve to canonical IDs rather than duplicating images. Original additions are `rps-rock`, `rps-paper`, `rps-scissors`, `element-flame`, `element-water`, `element-leaf`, `basketball`, `soccer-ball`, `baseball`, `tennis-ball`, `eight-ball`, and `person-running`.

## Usage

Open a generated app and **tap its icon beside the title**. The picker offers touch/keyboard search, paged previews, light/dark support, and Auto to restore an inferred icon. Searching `ball` or `person` works through aliases and tags. Choosing a logo updates the app's `icon`, preserves its contents, and persists to its current profile.

For app definitions, use `app.icon` for the wheel/header logo, optional `component.icon` for leading symbols, and optional collection `item.icon` for illustrated entries/cards. The `illustration` component provides a standalone asset/caption. All names are resolved and validated against this catalog; files, URLs, embedded SVG/code, and unknown IDs are rejected. Omitted icons retain compatibility with existing apps.

Search programmatically without importing pygame:

```python
from contract.asset_catalog import search, catalog
print(catalog()['count'])
print(search('basketball', 12))
```

Rendering uses `firmware/icon_assets.py`. Its lazy source cache holds at most 96 masks and the size/color cache holds 192 rendered surfaces. Icons follow the current monochrome palette, including inverted selected buttons/wheel nodes. The packed PNGs need neither network access nor an SVG parser on the Pi. The full pack is about 5 MB on disk; it is never decoded into memory all at once.

Gemini gets at most 64 relevant catalog entries per request rather than all IDs in every schema. Runtime validation accepts the full catalog and aliases. Search/category matching can be improved independently of the image pack.

## Rebuild

From the repository root, using the configured pygame environment:

```sh
.venv/bin/python sim/build_icon_catalog.py
```

This downloads the exact pinned archive and verifies SHA-256 before processing. For an existing download:

```sh
.venv/bin/python sim/build_icon_catalog.py --archive /path/to/lucide-static-1.59.0.tgz
```

The builder rejects unexpected/empty images and writes a deterministic ZIP with fixed member timestamps. Changing upstream versions requires explicitly reviewing/updating the version and digest, regenerating the catalog, checking license changes, and running `firmware/test_icon_assets.py`. Keep this directory with deployment source; downloaded speech models and other unrelated assets remain excluded.
