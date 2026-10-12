# VectorCraft CLI workflow

Checked against installed `vectorcraft-cli 0.10.0` and upstream commit `8715130c8b11bace7e72860a3b15b893deebbb36` on 2026-10-12. Installed help and command catalogue own exact syntax; the upstream default branch can be newer than a packaged build.

## Setup

Install a trusted [release](https://github.com/storytold/vectorcraft/releases), verify its published checksums, and put `vectorcraft-cli` on PATH. The desktop app alone may not put the CLI on PATH. From a source checkout, build `cargo build --release -p vectorcraft-cli` and add that checkout's `target/release` to PATH.

```sh
vectorcraft-cli --version
vectorcraft-cli --help
vectorcraft-cli commands
```

`commands` prints a JSON catalogue with IDs, parameter descriptions, and enablement. Unlike PhotoCraft, it does **not** offer `--json --filter`; search/filter the returned JSON with the harness. `enabled: false` with `no document open` is discovery context, not proof the command cannot run after opening a document. Query units/ranges instead of copying another app's parameters.

If the CLI is absent, direct SVG authoring still works. Report that native editing/rendering is unavailable; do not auto-install it or flatten an editable source to fake support.

## Create a badge and export it

```sh
vectorcraft-cli run \
  --cmd file.new --params '{"title":"Badge","width":64,"height":64,"units":"Pixels"}' \
  --cmd shape.ellipse --params '{"x":8,"y":8,"width":48,"height":48}' \
  --cmd paint.setFill --params '{"color":"#2563eb","ids":["$1.id"]}' \
  --export badge.vectorcraft \
  --export badge.svg \
  --export badge.png --scale 4
vectorcraft-cli info badge.vectorcraft
```

The ellipse's returned ID is referenced by `$1.id`. References count **command/export steps** from 0, not the initial `--in` open. An export also occupies a step, so keep references aligned when inserting steps. Each `--params` belongs to the immediately preceding `--cmd`; pass each JSON value as one argument token. This is native step-result resolution, not shell substitution; use `$$` for a literal leading dollar sign in a parameter string.

Coordinates are document space; numeric dimensions in engine commands are generally points. In the inspected CLI's exports, SVG uses one SVG unit per document point, and default raster scale is one pixel per point; `--scale 4` makes the 64-unit artboard a 256-pixel preview. `--scale` applies to raster export resolution, not to editable geometry, and is parsed for the entire run even when supplied after an export.

Save `.vectorcraft` as the editable master for live features. A generated preview is not reviewed until the harness opens it. Check shape bounds, optical alignment, stroke, color, alpha, and export warnings.

## Inspect and edit existing art

```sh
vectorcraft-cli info source.svg
vectorcraft-cli run --in source.svg \
  --cmd document.inspect --params '{"depth":2,"childLimit":20}'
```

Use `document.node {"id":...,"summary":true}` for focused reads on large documents. IDs can change across imports; inspect the actual source used for the next edit. For recoloring, pass explicit object IDs to `paint.setFill`. For transforms, discover `object.transform`'s affine matrix schema and pass explicit IDs. Inspect whether the operation targets an object, a group, a compound path, or the current selection. Preserve hidden/locked objects unless the brief requires otherwise.

For an intentional whole-art recolor:

```sh
vectorcraft-cli run --in source.svg \
  --cmd select.all \
  --cmd paint.setFill --params '{"color":"#2563eb"}' \
  --export recolored.vectorcraft \
  --export recolored.svg
vectorcraft-cli convert recolored.svg recolored-preview.png --scale 4
```

Each run has a fresh session. Put selection-dependent edits in the same run; save/reopen a native master for later calls. For a small SVG attribute edit, use direct source editing instead of engine round-tripping.

## Format and safety boundaries

- `convert IN OUT` exports by filename extension; `info FILE` reports import warnings, artboards, fonts, and object counts. `run` emits JSON per open/command/export step. Warnings may be nested in these result objects, not just stderr.
- PDF conversion exports every artboard by default; other formats generally use the first. `convert --artboard I` uses **0-based** indices; `--range "1-3,5"` uses **1-based** artboards. For exact multi-artboard SVG/raster behavior, discover `document.export` or `document.exportForScreens` and inspect the returned file list; do not guess filenames.
- `convert --outline-text` outlines SVG text. Keep a separate editable master. Fonts and renderer differences can change the appearance; compare before and after.
- SVG exports can retain VectorCraft editing metadata or rasterize unsupported effects. Browser fidelity and native editability are separate requirements. Read `document.formats`/`file.formatOptions` for available SVG options; use only options supported by the installed build.
- `.ai` is not a guarantee of full Illustrator editing-data interoperability. Imported SVG/PDF/EPS/Affinity art can lose features; inspect warnings. Keep the original, avoid same-file conversion, and do not use `--replace-lossy` without explicit authorization.
- CLI commands can overwrite destinations and read/write additional files (linked assets, packages, preset libraries, plug-ins). Neither the JSON bridge nor raw `run`/`convert` enforces workspace roots. Run only reviewed commands with authorized paths; failures may leave partial outputs. Do not install/execute untrusted plug-ins or auto-fetch external SVG resources.

## Runtime and persistent MCP

The bundled `scripts/tool.py` is a JSON-in/JSON-out one-shot bridge. It resolves `vectorcraft-cli` on PATH, does not invoke a shell, captures stdout/stderr, and times out the subprocess after 590 seconds (manifest limit: 600 seconds). It does not install software or enforce overwrite/file-access policy. Use `vectorcraft` with `command` and `arguments` as described in `SKILL.md`.

For persistent selection, targeted reads, and collaboration, register VectorCraft's own stdio MCP server:

```sh
vectorcraft-cli mcp --headless \
  --automation-read-root /absolute/project \
  --automation-write-root /absolute/project/output
```

Roots must already exist. When either root is supplied, omitted read/write authority grants none of that access. These flags imply headless; do not combine them with `--connect`. Without roots/mode, MCP tries a running desktop app before falling back to headless; use explicit headless mode to avoid accidentally modifying a live session. Confinement is an application path policy, not an OS sandbox against concurrent filesystem changes.

Consult upstream [MCP documentation](https://github.com/storytold/vectorcraft/blob/main/docs/mcp.md) for persistent tools/resources and desktop connection behavior. Do not wrap this long-lived server inside the one-shot runtime tool.
