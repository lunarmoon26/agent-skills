# PhotoCraft CLI workflow

## Setup and scope

Install a trusted build from [PhotoCraft releases](https://github.com/storytold/photocraft/releases), verify the published checksums, and ensure `photocraft-cli` is on PATH. Packaging varies by platform; installing the desktop app does not by itself prove the CLI is on PATH. Alternatively, from a checkout of the upstream repository:

```sh
cargo build --release -p photocraft-cli
# Add that checkout's target/release directory to PATH.
photocraft-cli --version
photocraft-cli --help
```

Do not download or install software during an image-editing tool call. If the CLI is absent, report the dependency and use Pillow only where it can preserve the requested intent; it is not a fallback for layered PSD editing.

This guide was checked against installed CLI `0.8.2 (d43db3e15, 2026-10-12)` and upstream commit `cd36d1ea0d2ea523df4f231f08eafda73d0fe921`. Treat the installed executable's help and command registry as authoritative for syntax; alpha builds change quickly.

## Inspect → discover → edit → render → verify

1. Inspect the input document and its layer tree, color mode, depth, dimensions, and warnings:

   ```sh
   photocraft-cli info input.psd --compact
   ```

2. Discover the exact engine IDs and parameter descriptions for the operation:

   ```sh
   photocraft-cli commands --json --filter layer.newAdjustmentLayer.curves
   photocraft-cli run --help
   ```

   Registry entries can report `enabled: false` / `no document open` during discovery: this is context, not proof the command is unavailable after opening a document. Do not invent parameters from Photoshop's UI or assume every wired command has full behavior. Read numeric units/ranges from the registry (some colors use 0–1, curves use 0–255).

3. Prefer adjustment layers over destructive pixel adjustments. Repeated `--cmd` flags execute in order; each `--params` JSON value belongs to the preceding command. Each `run` opens a fresh document; separate calls do not share selection, active-layer, or document state.

   ```sh
   photocraft-cli run input.psd \
     --cmd layer.newAdjustmentLayer.curves \
     --params '{"points":[[0,0],[64,48],[192,212],[255,255]]}' \
     --out edited.pcraft
   photocraft-cli convert edited.pcraft preview.png
   photocraft-cli info edited.pcraft --compact
   ```

   Keep `.pcraft` as an editable master, or `.psd` when Photoshop interchange is required. Inspect layer targeting before edits: use IDs from document inspection and discovered selection commands, not guessed indices. For a new canvas, `run --new '{"width":1200,"height":630,"background":"transparent"}' --out canvas.pcraft` creates and saves one without an input file.

4. View the exported preview with the harness's image viewer. Check dimensions, intended changes, alpha edges, text/fonts, layer/mask behavior, and import/export warnings. Compare with a baseline render for fidelity-sensitive edits. A saved PSD need not be byte-identical or render exactly like Photoshop; do not promise lossless interchange. Preserve the original.

## Migration from the bundled photo CLI

`photo_process` and `photo.py` expose only `resize`, `key-luminance`, and `sprite-grid`. The standalone `inspect`, `key-color`, `flood-fill`, `mask`, and `trim` operations are removed without compatibility aliases. Update saved tool requests and scripts; unsupported commands fail nonzero. PhotoCraft is now required for these general editing workflows. The remaining Pillow code is for specialized asset packaging, explicit luminance/alpha normalization, and sprite metadata—not an alternative editing engine.

| Removed command | PhotoCraft workflow | Important difference |
| --- | --- | --- |
| `inspect` | `photocraft-cli info input.png --compact` | Document/layer info, not the previous Pillow `size`/`frames` record schema; inspect animation separately when relevant |
| `key-color` | `filter.other.colorToAlpha` | Thresholds are 0–1, not the old RGB-distance tolerance/feather; color decontamination can change RGB |
| `flood-fill` | `paint.bucket` for color; `select.magicWand` → `edit.clear` for transparent removal | No documented match/ignore-alpha or 4/8 connectivity switches; do not translate old tolerance/alpha settings as equivalent |
| `mask` | `edit.fill` with `preserveTransparency` for silhouette recoloring | Preserves existing alpha; does not implicitly derive alpha from luminance. Use retained `key-luminance` explicitly for luminance-derived alpha and verify its differing transfer function. Former `--alpha-source inverse-luminance` and `--opacity` have no drop-in migration here; construct and verify an explicit native mask/opacity workflow instead |
| `trim` | `image.trim` → `image.canvasSize` for padding/square canvas | Inspect dimensions after trim, then calculate canvas size; sprite-grid still trims its own cuts internally |

Discover these command schemas on the installed build before use. The following examples target a flat PNG's active pixel layer. For layered/locked-background inputs, inspect and target/unlock the appropriate layer first; never apply these examples indiscriminately to every layer. Every output path must be fresh or explicitly approved for replacement: PhotoCraft does not inherit Pillow's overwrite guard.

```sh
# Replace a seed-connected color region. Coordinates must be measured from the input.
photocraft-cli run input.png --cmd paint.bucket \
  --params '{"x":0,"y":0,"tolerance":0,"contiguous":true,"antiAlias":false,"color":"#112233"}' \
  --out filled.png

# Remove only the seed-connected backdrop, not enclosed matching-color regions.
photocraft-cli run input.png --cmd select.magicWand \
  --params '{"x":0,"y":0,"tolerance":0,"contiguous":true,"antiAlias":false}' \
  --cmd edit.clear --cmd select.deselect --out transparent.png

# Remove a known background color globally; inspect fringes/RGB afterward.
photocraft-cli run input.png --cmd filter.other.colorToAlpha \
  --params '{"color":"#000000"}' --out keyed.png

# Recolor an existing alpha silhouette without flattening its transparency.
photocraft-cli run input.png --cmd edit.fill \
  --params '{"contents":"color","color":"#112233","preserveTransparency":true}' \
  --out recolored.png

# Trim transparent margins; inspect the result before calculating any padding.
photocraft-cli run input.png --cmd image.trim \
  --params '{"basedOn":"transparent"}' --out trimmed.png
photocraft-cli info trimmed.png --compact
```

For 12-pixel padding, new width/height are trimmed width/height plus 24. For a padded square, both dimensions are `max(trimmed width, trimmed height) + 24`. Use `image.canvasSize` with those computed pixel dimensions, `anchor:"center"`, and `extensionColor:"transparent"`; do not guess values from a scaled preview.

Live tests on CLI 0.8.2 cover dimensions/alpha after trim, alpha-preserving fill, exact-color contiguous bucket fill, global black-to-alpha, and enclosed-region preservation after Magic Wand/clear. These are focused fixtures, not proof of equivalence for arbitrary feathering, profiles, anti-aliasing, animation, or layered backgrounds. Keep originals and inspect real-image exports.

## Batch actions

Save a reviewed JSON action list, for example `grade.json`:

```json
[
  {"command":"layer.newAdjustmentLayer.curves","params":{"points":[[0,0],[64,48],[192,212],[255,255]]}}
]
```

```sh
photocraft-cli batch --actions grade.json --in ./raw --out ./graded --format png
```

Test the action on one representative input before a full batch. Use a new output directory; do not use `--in-place`. Existing output files can be replaced, and commands inside actions may perform additional writes. Review every destination, not just the batch output folder. Failed batches can leave partial outputs; inspect errors and per-file results before retrying.

## Formats and warnings

- `convert` changes format; `run` edits and optionally saves; `info` inspects; `commands` discovers the engine. These and `batch` are the only subcommands exposed by the runtime bridge.
- TIFF export is flat unless `--tiff-layers` is supplied. WebP is lossless by default; `--quality 1..100` requests lossy WebP (or sets JPEG quality).
- Preserve higher bit depth/color modes in an appropriate editable master. Eight-bit delivery formats can reduce depth; check warnings instead of assuming all conversions preserve precision or ICC behavior.
- Missing fonts may render using fallback faces. Install the requested fonts or obtain approval for a substitution; do not call the result an exact match.
- Codec support is build-dependent: HEIC input and AVIF output may require build features; AVIF decoding is unavailable in the inspected upstream build contract. Use Pillow for AVIF workflows it supports, not to flatten a layered master.

## Runtime and persistent sessions

The `photocraft` tool accepts native CLI tokens, for example:

```json
{"command":"run","arguments":["input.psd","--cmd","layer.newAdjustmentLayer.curves","--params","{\"points\":[[0,0],[64,48],[192,212],[255,255]]}","--out","edited.pcraft"]}
```

It resolves `photocraft-cli` from the host's PATH, captures stdout/stderr, and imposes a 590-second subprocess timeout (within the manifest's 600-second limit). It does not invoke a shell, auto-install dependencies, enforce workspace roots, or guard overwrites. Only run trusted commands/action files with authorized paths. `warnings` retains all stderr lines, not only messages prefixed `warning:`. Errors go to stderr with a nonzero bridge exit; a failure may still have written files.

For persistent layer/selection state or desktop collaboration, use PhotoCraft's own MCP server instead of nesting it in the one-shot runtime tool:

```sh
photocraft-cli mcp --automation-read-root /absolute/project --automation-write-root /absolute/project
```

Register this stdio command using the harness's MCP configuration. Native MCP supports workspace-root restrictions; raw `run`/`batch` do not. Desktop bridging additionally needs the upstream loopback control channel and its authentication token. Consult the upstream [CLI guide](https://github.com/storytold/photocraft/blob/main/book/src/automation/cli.md) and [control protocol](https://github.com/storytold/photocraft/blob/main/docs/control-protocol.md); do not start an unauthenticated network service.

## VectorCraft handoff

[VectorCraft](https://github.com/storytold/vectorcraft) is the related vector illustration engine, not another photo filter backend. Use the `vector-illustration` skill for logos, editable paths, artboards, and SVG/PDF deliverables, including its separate `vectorcraft` runtime tool. Retain the vector source. Its CLI syntax differs from PhotoCraft:

```sh
vectorcraft-cli --help
vectorcraft-cli run --in illustration.vectorcraft --export illustration.svg
vectorcraft-cli mcp --automation-read-root /absolute/project --automation-write-root /absolute/project
```

These commands follow upstream documentation; this skill does not expose a VectorCraft runtime tool. Verify the installed build's help before use. Illustrator `.ai` interchange is limited (PDF-compatible files are not a guarantee of Illustrator editing-data fidelity). Do not claim complete Illustrator parity. Use PhotoCraft when the task is raster compositing; use VectorCraft when editable vector geometry is the deliverable.
