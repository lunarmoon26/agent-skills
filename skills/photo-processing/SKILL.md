---
name: photo-processing
description: Use for photo, image, texture, and icon editing, including Photoshop-style layered PSD/PSB editing, adjustment layers, filters, masks, compositing, and batch actions with PhotoCraft CLI; or resize, crop, convert, optimize, recolor, flood fill, background transparency, sprite splitting, and CSS sprite geometry with the bundled Pillow tools. Trigger even when the user does not name a file format. For Illustrator-style vector illustration, see the VectorCraft handoff.
compatibility: Bundled tools require uv and Python 3.11–3.14; advanced editing additionally requires photocraft-cli on PATH. Pillow is pinned with PEP 723 metadata.
---

# Photo Processing

Choose the smallest engine that preserves the user's editing intent:

- **Pillow (`photo.py` / `photo_process`)**: flat-image resizing, transparency, flood fill, icon normalization, and sprite geometry. It writes a suffixed file by default and refuses to replace an existing file unless `--overwrite` is explicit.
- **PhotoCraft (`photocraft-cli` / `photocraft`)**: layered documents, PSD/PSB, adjustment layers, selections/masks, type, filters, compositing, and recorded batch actions. Keep an editable master and export a separate preview/delivery image. Read [the PhotoCraft workflow](references/photocraft.md) before using it.
- **VectorCraft**: Illustrator-style paths, Bézier editing, vector booleans, artboards, and SVG/vector deliverables. See [the vector handoff](references/photocraft.md#vectorcraft-handoff); do not flatten a vector master just to use the raster tools.

PhotoCraft is early alpha, not a guaranteed professional Photoshop replacement. Inspect imports and rendered exports; do not infer fidelity from a successful exit code.

Set `PHOTO_SCRIPT` to this skill's bundled `scripts/photo.py` file, then use it in each command:

```sh
PHOTO_SCRIPT=/absolute/path/to/photo-processing/scripts/photo.py
uv run --script "$PHOTO_SCRIPT" <command> ...
```

Inspect before choosing geometry or an output format:

```sh
uv run --script "$PHOTO_SCRIPT" inspect path/to/image.png
```

Hosts that support executable skills may call `photo_process` or `photocraft` from `skill-runtime.json`. Both accept `command` plus `arguments` (each following CLI token as a separate string); neither bridge invokes a shell. Run the repository's documented runtime `prepare` command once before the first tool call so later `uv` execution stays offline. PhotoCraft is a separately installed native executable, not a Python dependency; its bridge requires the runtime's `process` and filesystem capabilities. It returns stdout as `messages`, parsed JSON as `records`, and stderr as `warnings`; CLI failures exit nonzero, not as successful results. Long-lived `mcp`/`serve` commands are not exposed through this one-shot tool.

The script preserves EXIF orientation. It rejects animated inputs unless `--first-frame` is specified, avoiding accidental animation loss. Alpha cannot survive JPEG or BMP export; select `png`, `webp`, `avif`, or `tiff` for transparent output.

## Resize And Convert

Use `resize` for one image, multiple files, or an input directory. `contain` preserves aspect ratio inside the bounds; `cover` fills and center-crops; `fill` stretches; `inside` avoids upscaling. Add `--pad` to make a contain/inside result exactly the requested dimensions.

```sh
# Generate social-card JPEG and WebP exports from one source.
uv run --script "$PHOTO_SCRIPT" \
  resize artwork.png --width 1200 --height 630 --fit cover --format jpg,webp --output-dir build/social

# Preserve aspect ratio within 512 px, then place it on a transparent square canvas.
uv run --script "$PHOTO_SCRIPT" \
  resize logo.png --width 512 --height 512 --fit contain --pad --background '#00000000' --format png

# Create a multi-resolution ICO favicon. Use a high-resolution square source.
uv run --script "$PHOTO_SCRIPT" \
  resize mark.png --width 512 --height 512 --fit contain --format ico --ico-sizes 16,32,48,64,128,256
```

Use `--output desired-name.webp` for a single intentional output name. In batch operations use `--output-dir`; an input directory is accepted, and `--recursive` includes nested files.

## Transparency And Icon Masks

Use `flood-fill` for a Photoshop Magic Wand-style **contiguous** replacement. It samples the pixel at `--x, --y`, finds the connected region whose channels are each within `± --tolerance` of that fixed seed color, and replaces only that region. Matching the fixed seed prevents color drift across a gradient. Eight-way connectivity includes diagonally touching pixels by default; use `--connectivity 4` for edge-sharing pixels only.

`--alpha-mode match` (the default) treats alpha as another channel and preserves transparency boundaries. Use `--alpha-mode ignore` when hidden RGB should match regardless of opacity. The replacement color accepts alpha, so `#00000000` makes the selected region transparent. Coordinates are intrinsic image pixels; inspect the image rather than estimating from a scaled preview.

```sh
# Remove only the near-black backdrop connected to the center seed. Enclosed black artwork remains opaque.
uv run --script "$PHOTO_SCRIPT" \
  flood-fill desktop.png --x 960 --y 540 --tolerance 8 \
  --color '#00000000' --alpha-mode ignore --output desktop-transparent.png

# Recolor one connected near-white area while respecting alpha boundaries.
uv run --script "$PHOTO_SCRIPT" \
  flood-fill icon.png --x 24 --y 18 --tolerance 12 \
  --color '#ff3b30ff' --alpha-mode match --output icon-red.png
```

Unlike `key-color`, which changes every matching pixel in the image, `flood-fill` changes only the seed-connected region. This corresponds to Magic Wand with **Contiguous** enabled; tolerance is an explicit per-channel range rather than an undocumented color-distance metric.

Use `key-color` when a known color is the background. `--tolerance` removes all RGB values within that distance and `--feather` fades the following distance band to preserve anti-aliased edges.

```sh
# Remove black from line art; retain slightly off-black edge pixels as a soft alpha fringe.
uv run --script "$PHOTO_SCRIPT" \
  key-color weather-reference.png --color '#000000' --tolerance 10 --feather 18 --output weather-alpha.png

# Convert a dark space-image backdrop to alpha using perceived brightness.
uv run --script "$PHOTO_SCRIPT" \
  key-luminance galaxy.webp --start 2 --end 255 --gamma 2.2 --blur 1.2 --output galaxy-alpha.png
```

By default, `key-luminance` multiplies the calculated matte by the image's existing alpha. Use `--alpha-mode replace` for a black-backed image whose RGB colour should become the new transparency, ignoring existing alpha. Replacement mode derives alpha from sRGB luminance and normalizes visible RGB so the colour is not attenuated twice. `--alpha-floor` removes low-level background noise without remapping brighter values:

```sh
uv run --script "$PHOTO_SCRIPT" \
  key-luminance hud-layer.png --alpha-mode replace --alpha-floor 2 --output hud-luminance-alpha.png
```

Replacement mode is for a final black-backed image or an already flattened layer group. If several translucent layers occlude each other, composite them with their original alpha first, then apply luminance replacement to the completed group; processing each layer independently changes occlusion.

Use `mask` to make a one-color icon. `--alpha-source alpha` preserves an existing transparent silhouette. For white line art on an opaque black background, use `--alpha-source luminance`; use `inverse-luminance` for dark artwork on a light background.

```sh
uv run --script "$PHOTO_SCRIPT" \
  mask weather-reference.png --color '#72ffff' --alpha-source luminance --output weather-cyan.png
```

After creating transparency, use `trim` to remove empty edges and optionally normalize an icon to a padded square canvas:

```sh
uv run --script "$PHOTO_SCRIPT" \
  trim weather-cyan.png --padding 12 --square --output weather-icon.png
```

## Sprite Sheets And Icon Grids

Use `sprite-grid` for regular icon grids. It cuts individual images, emits metadata with exact source rectangles and CSS background positions, and can render an annotated preview for checking offsets. First make an alpha-capable version if the sheet needs its black or white background removed.

Specify the measured grid origin, crop size, and gaps. When there are no gaps, omit `--cell-width` and `--cell-height` to derive them from the image dimensions. Labels are optional comma-separated names in left-to-right, top-to-bottom order.

```sh
uv run --script "$PHOTO_SCRIPT" \
  sprite-grid weather-alpha.png --columns 8 --rows 4 \
  --origin-x 100 --origin-y 63 --cell-width 175 --cell-height 175 --gap-x 58 --gap-y 75 \
  --prefix weather \
  --output-dir Assets/weather-icons --trim --padding 8 --square \
  --metadata Assets/weather-icons/weather.json \
  --css Assets/weather-icons/weather-sprites.css --css-class weather-sprite \
  --image-url Weather_icons_alpha.png --preview Assets/weather-icons/weather-guide.png
```

`--labels` must include exactly one name per grid cell. Omit it if stable row/column names such as `r00-c00` are sufficient. The generated JSON has each cell's `sourceRect`, `outputSize`, and `backgroundPosition`; CSS keeps the original grid geometry even when `--trim` changes the standalone cut dimensions.

Use the annotated `--preview` to adjust origin, cell size, and gaps before committing assets. Do not guess crop geometry from a scaled browser preview; use intrinsic pixels reported by `inspect`.

## Working Rules

### Edge-preserving preparation for vector tracing

For noisy flat surfaces, use the optional `scripts/trace_prepare.py` helper to write a separate bilateral-filtered PNG candidate:

```sh
uv run --script /absolute/path/to/photo-processing/scripts/trace_prepare.py \
  reference.png prepared.png --diameter 5 --sigma-color 20 --sigma-space 3
```

Requires `uv`, Python 3.11–3.14, pinned Pillow and OpenCV (PEP 723 dependencies, downloaded on first use); it is not exposed by `photo_process`. It preserves EXIF-oriented dimensions, never replaces the source or existing outputs, and rejects animation, non-opaque alpha, and ICC-tagged input. Output is untagged RGB PNG; the parent directory must exist. Prepare a controlled sRGB input first when color profiles matter. Failures exit nonzero; an interrupted write can leave a partial output. Do not use this opaque-only helper on transparent artwork or blur linework indiscriminately.

Filtering can reduce tracing speckles but cannot reconstruct gradients from flat-color SVG patches. Compare the final vector render with the original; preserve weak detail and intentional cel shading. See the vector-illustration skill's `references/smoothing.md` for diagnosis, bounded retracing, gradient reconstruction, and filter-export tradeoffs.

### Output safety

- Keep source assets unchanged. Write outputs beside the source with a suffix or into a project asset directory.
- PhotoCraft's raw CLI can replace existing destinations without confirmation, and engine commands/actions can write paths beyond `--out`. Review all commands, parameters, actions, and destinations first. The bridge is not a filesystem sandbox or an overwrite guard.
- Use PNG, WebP, or AVIF when subsequent steps need transparency. JPEG/BMP exports flatten alpha onto `--background` (white by default).
- Use a high-resolution source for ICO files; the script writes each requested `--ico-sizes` resolution.
- State input and output paths plus output dimensions/formats in the final response. Mention any visual tuning that still needs human approval.
