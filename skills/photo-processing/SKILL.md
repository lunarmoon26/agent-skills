---
name: photo-processing
description: Use when the user wants to resize, crop, convert, optimize, recolor, mask, flood fill, use a Magic Wand-style contiguous color selection, make image backgrounds transparent, create transparent icon assets, split a sprite sheet, calculate icon crop offsets, or generate CSS sprite positions for PNG, JPEG, WebP, AVIF, TIFF, BMP, GIF, or ICO files. Use this skill for image/photo/texture/icon asset editing, including when the user does not name a file format.
compatibility: Requires `uv`; bundled scripts pin Pillow with PEP 723 metadata.
---

# Photo Processing

Use the bundled script for deterministic, non-destructive image work. It writes a suffixed file by default and refuses to replace an existing file unless `--overwrite` is explicit.

Set `PHOTO_SCRIPT` to this skill's bundled `scripts/photo.py` file, then use it in each command:

```sh
PHOTO_SCRIPT=/absolute/path/to/photo-processing/scripts/photo.py
uv run --script "$PHOTO_SCRIPT" <command> ...
```

Inspect before choosing geometry or an output format:

```sh
uv run --script "$PHOTO_SCRIPT" inspect path/to/image.png
```

Hosts that support executable skills may call `photo_process` from `skill-runtime.json`. Pass the same subcommand in `command` and every following CLI token as a separate string in `arguments`; the bridge never invokes a shell. Run the repository's documented runtime `prepare` command once before the first tool call so later `uv` execution stays offline.

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

- Keep source assets unchanged. Write outputs beside the source with a suffix or into a project asset directory.
- Use PNG, WebP, or AVIF when subsequent steps need transparency. JPEG/BMP exports flatten alpha onto `--background` (white by default).
- Use a high-resolution source for ICO files; the script writes each requested `--ico-sizes` resolution.
- State input and output paths plus output dimensions/formats in the final response. Mention any visual tuning that still needs human approval.
