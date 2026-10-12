# Direct SVG authoring and editing

## Inspect before changing

- Read the actual SVG, not only a screenshot. Record `viewBox`, width/height, groups, transforms, reusable definitions, text, clipping/masks, gradients, and linked assets.
- Preserve existing IDs used by CSS, JavaScript, animation, or `<use>` references. Change the smallest relevant element/attribute; avoid rewriting an entire exported illustration for a small edit.
- Distinguish the coordinate system from display dimensions: a `viewBox="0 0 24 24"` can render at many CSS sizes. Do not stretch geometry to satisfy a new display size.

## Create portable artwork

- Include `xmlns="http://www.w3.org/2000/svg"` and a deliberate `viewBox`. Use basic shapes for editable geometry; paths for custom contours. Keep precision sufficient for small curves without unnecessary digits.
- Use groups for logical parts. Keep defs references unique; prefix IDs when multiple SVGs may be inlined into one page. Ensure every `url(#id)` / `href="#id"` resolves.
- Use a consistent stroke width, linecap, linejoin, and fill rule. Decide whether strokes scale with the artwork; use `vector-effect="non-scaling-stroke"` only when fixed screen-space strokes are intended.
- Keep backgrounds transparent unless requested. `fill="none"` means no fill; it is not the same as an opaque white shape. Check compound-path holes (`evenodd` versus winding), clipping, and mask luminance/alpha semantics in the target renderer.
- Keep live text when editing is required and fonts are available. For portable final outlines, export a separate outlined copy; retain text in the editable master and check font licensing. Text-to-path is not reversible text editing.
- For themable single-color inline icons, use `currentColor` when the consuming UI expects it. For standalone illustration exports, use explicit colors unless theme integration is required.
- Avoid embedded raster images for vector-only deliverables. If needed, disclose them and choose embedding versus authorized local links intentionally. Never embed secrets, local absolute paths, or remote tracking assets.

Example source (an editable 24-unit icon with round stroke geometry):

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path id="mountains" d="M3 18 9 8 13 14 16 10 21 18Z"
        fill="none" stroke="#2563eb" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

For inline HTML, wire accessible labeling in the consuming component (`role="img"` with an accessible name for meaningful artwork; `aria-hidden="true"` for decorative icons). For `<img>`, set appropriate `alt` in the HTML. A standalone `<title>` alone does not cover every embedding context.

## Validation

1. Parse XML using the project's tooling. Reject DTD/entity declarations and active content before rendering untrusted inputs. Do not execute scripts or fetch external resources simply to inspect an SVG.
2. Check root namespace, nonempty positive viewBox dimensions, valid references, output dimensions, and intended background. Do not assume parsing catches malformed path data or CSS.
3. Render in the intended browser/viewer. Inspect intended small size and enlarged size, light/dark backgrounds as applicable, and text/font availability. Use the project's visual/browser tests where present.
4. If VectorCraft is installed, `vectorcraft-cli info asset.svg` surfaces import warnings, and `vectorcraft-cli convert asset.svg preview.png --scale 4` provides an additional preview—not a substitute for browser verification.
5. Optimize only after approval of geometry. Keep IDs and metadata needed by consumers. Compare before/after rendering; do not run an unreviewed optimizer that silently outlines text, removes accessibility, changes precision, or breaks references.

Never equate XML validity, a clean CLI exit, or smaller bytes with a faithful rendered result.
