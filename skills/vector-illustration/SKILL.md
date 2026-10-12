---
name: vector-illustration
description: Use when creating or editing vector illustrations, SVG files, logos, icons, diagrams, badges, patterns, posters, Bézier paths, gradients, clipping masks, or artboards, or recreating a reference image as closely as possible with editable vector art. Covers direct SVG authoring and Illustrator-style gradients, blends, meshes, repeats, envelopes, perspective, tracing, recoloring, and export with VectorCraft CLI. Trigger even when no file format is named; use photo-processing for raster photo edits instead.
compatibility: Direct SVG authoring needs file-editing tools and a viewer; the optional runtime requires uv, Python 3.11–3.14, and vectorcraft-cli on PATH.
---

# Vector Illustration

Create editable vector artwork, not a raster image wrapped in an SVG. Preserve existing visual language and source files. VectorCraft is alpha; successful export is not proof of fidelity or Illustrator parity.

## Choose the workflow

| Task | Preferred path |
| --- | --- |
| Small icon, logo, diagram, web SVG, or precise source-level change | Author/edit SVG directly; see [SVG guidance](references/svg.md) |
| Rich illustration, multiple artboards, path booleans, live appearance/effects, or native editable master | VectorCraft; see [CLI workflow](references/vectorcraft.md) |
| Scenic/neon posters, ribbons, mandalas, warped type, mesh shading, or perspective scenes | [Example-derived scenarios](references/scenarios.md), then discover the installed command schemas |
| Recreate an image faithfully as editable vector art | [Reference reconstruction](references/reconstruction.md); measure and compare before adding detail |
| Persistent object/selection state or live app collaboration | VectorCraft's own MCP server, with authorized read/write roots |
| Photo retouching, PSD layering, pixel masks, sprite cutting | `photo-processing`, not this skill |

Do not round-trip an existing SVG through VectorCraft for a one-line color change. Import/export can rewrite structure or drop unsupported features. Never hand-edit VectorCraft's native JSON based on guessed model fields; use its engine commands.

## Work loop

1. **Inspect the brief and source.** Establish subject, style, palette, canvas/viewBox, target size, background, editable-text needs, and delivery formats. Inspect existing SVG elements or VectorCraft's artboards/object tree before editing. Ask only if an unresolved requirement blocks progress; otherwise choose local defaults and state them.
2. **Build the composition.** Use deliberate silhouette, spacing, hierarchy, and a consistent stroke/shape vocabulary. For an icon family, keep common canvas, optical margins, stroke widths, and detail density. Avoid adding arbitrary gradients, shadows, or decorative elements to a simple brief.
3. **Edit non-destructively.** Keep source unchanged by default. Use meaningful SVG IDs/groups or named VectorCraft objects. Use discovered IDs and command schemas rather than guessed indices or Photoshop syntax. Retain live text and effects in the master unless the user requests destructive conversion.
4. **Render and inspect.** View the result at intended size and enlarged. Check clipping, stroke edges, holes/fill rules, alignment, text/font fallback, contrast, and transparent/light/dark backgrounds. XML parsing verifies syntax, not appearance. For web SVG, test in the intended browser; a VectorCraft PNG preview alone does not establish browser equivalence.
5. **Deliver source plus needed exports.** Keep `.svg` as an editable master for simple SVG-first work; keep `.vectorcraft` for native live features. Export SVG/PDF and raster previews separately. Do not promise Illustrator editing-data compatibility or a purely vector export when effects/images rasterize.

## Runtime tool

Hosts can call `vectorcraft` from `skill-runtime.json` with `command` (`commands`, `info`, `run`, or `convert`) and `arguments` (separate native CLI tokens). Example:

```json
{"command":"run","arguments":["--in","source.svg","--cmd","select.all","--cmd","paint.setFill","--params","{\"color\":\"#2563eb\"}","--export","recolored.svg"]}
```

This recolors **all selectable artwork**; for targeted changes inspect IDs and pass explicit `ids` to the paint command. The bridge runs a separately installed `vectorcraft-cli` from PATH without a shell or automatic installation. It returns stdout lines as `messages`, parsed JSON values as `records`, and stderr lines as `warnings`; inspect warnings inside native result records too. Errors exit nonzero. Long-lived MCP and benchmarking commands are not exposed.

Prepare the manifest using the repository's runtime `prepare` command before enabling it. Native CLI execution requires `process`, `filesystem-read`, and `filesystem-write` capabilities. Each `run` creates a fresh session: put dependent commands and exports in one call, or save and reopen a master. It is **not** an overwrite guard or filesystem sandbox: commands can write files beyond `--export`, and failures can leave partial files. Review all commands and destinations; do not run untrusted command lists, plug-ins, or active SVG content.

## Completion

Report editable source paths, exported paths, canvas/artboard dimensions, and which visual checks actually ran. Flag font substitutions, unsupported import/export features, embedded raster content, or remaining visual approval. Never describe an unviewed preview as visually verified.

For reference reconstruction, also deliver a same-size rendered preview and comparison artifacts. Name remaining mismatches rather than calling a rough recognizable silhouette a close match. The bundled `scripts/compare.py` creates side-by-side, overlay, and difference PNGs plus numerical diagnostics; see the reconstruction guide for usage. It requires pinned Pillow through `uv`, but no VectorCraft runtime changes.
