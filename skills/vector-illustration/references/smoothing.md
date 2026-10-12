# Patchy traces: diagnose before smoothing

Use when traced SVG colors look mottled, tiled, posterized, or separated by hairline seams. A smoother contour is not smoother shading. Do not promise that SVG optimization, more colors, or path simplification will recover the original surfaces.

## Choose the treatment

| Visible symptom | Likely mechanism | Preferred treatment | Does not solve it |
| --- | --- | --- | --- |
| Jagged silhouette/curves | Pixel-contour fitting | Selected-path Bézier cleanup; simplify with before/after checks | Recoloring |
| Tiny interleaved shades on a nominally flat surface | Source noise/compression plus quantization | Mild edge-preserving preprocessing, then retrace; selectively consolidate same-surface shades | Increasing palette indiscriminately |
| Large stair-step color patches across a soft tone | Gradient represented as discrete flat fills | Reconstruct that surface with a gradient or verified mesh | Simplifying anchors or joining identical fills |
| Thin cracks between adjacent polygons, varying by renderer/zoom | Anti-aliasing seams | Controlled overlap or small matching-color strokes | Gradient reconstruction |
| Deliberate hard-edged shadow/highlight | Cel shading | Preserve the boundary | Blanket smoothing |

Confirm the diagnosis against the original, at delivery size and enlarged. Separate noise, intentional texture, cel boundaries, and smooth illumination. Colors alone cannot identify surfaces: the same purple may occur on unrelated armor parts. Palette groups are not semantic groups.

## Route A: reduce noisy patches before tracing

When the raster original exists, prefer retracing it to rasterizing an already damaged SVG. Keep an untouched baseline and try at most two mild preprocessing candidates before switching to surface reconstruction. Bilateral filtering averages spatially close, similar colors while limiting mixing across strong edges; weak lines and low-contrast details can still disappear.

The photo-processing skill provides `scripts/trace_prepare.py`:

```sh
uv run --script /absolute/path/to/photo-processing/scripts/trace_prepare.py \
  reference.png prepared.png --diameter 5 --sigma-color 20 --sigma-space 3
```

This is an optional OpenCV/Pillow helper, not a new runtime tool. It preserves oriented dimensions and refuses existing destinations, source replacement, animation, transparency, and ICC-tagged input. Transparent images need alpha-aware filtering; do not silently composite them onto an opaque background. Prepare tagged images in a controlled sRGB workflow first. Compare the final traced result against the **original**, not merely the filtered candidate.

Discover the installed `imageTrace` schemas and presets. Use identical settings for baseline and filtered trials; record paths, anchors, bytes, time, and detail crops. Then vary one tracing parameter only if needed. Fewer colors can reduce speckles but increase banding; more colors can create more regions. Noise thresholds can erase lettering, holes, cables, and fasteners. Stop when important detail regresses, even if counts or mean pixel error improve.

VectorCraft already applies internal edge-preserving smoothing to continuous-tone color traces in the inspected source. Extra filtering is therefore an experiment, not a mandatory fix.

## Route B: smooth existing SVG shading with real gradients

For polished vector-only results, replace artificial tone patches **within one surface** with a cleaner surface path and appropriate `linearGradient`/`radialGradient` fill. Retain genuine hard shadows, highlights, linework, and occluders as separate paths above it. This is surface reconstruction, not a safe global XML substitution.

1. Identify a surface in the original and isolate its silhouette, holes, and overlap order. Inspect transforms, clipping, fill rules, opacity, and seam strokes in the SVG before editing.
2. Preserve a named copy in the working master. Build/union selected surface regions using engine booleans or author a measured new contour. Do not concatenate arbitrary path strings: overlaps, winding, and holes can change the result.
3. Sample interior colors along the actual shading direction, avoiding outlines and compression halos. Start with two or three stops; use flat fill if the original surface is flat. Use radial gradients only for genuinely radial lighting.
4. Prefer `gradientUnits="userSpaceOnUse"` for a gradient shared by several paths in the same coordinate system. Explicitly align gradient coordinates with group transforms. Default object-bounding-box gradients restart on each object's bounds and can produce new patch boundaries.
5. Remove only redundant tone regions and their seam strokes after the replacement looks correct. Keep hard shadow/highlight edges crisp, with linework and lettering above the fill. Clip where necessary to preserve the silhouette.
6. Render in the target browser, compare focus crops, then reopen/export the native master. Do not assume mesh or gradient import/export support from successful file creation.

Minimal gradient syntax (illustrative colors/coordinates, not a reconstruction):

```xml
<defs>
  <linearGradient id="panel-tone" gradientUnits="userSpaceOnUse"
                  x1="100" y1="200" x2="300" y2="260">
    <stop offset="0" stop-color="#8065b7"/>
    <stop offset="1" stop-color="#574085"/>
  </linearGradient>
</defs>
<path id="panel-surface" d="M100 200 H300 V260 H100 Z"
      fill="url(#panel-tone)"/>
```

Use native mesh shading only when linear/radial gradients are insufficient and the delivery renderer supports the exported result. Keep a compatible SVG fallback and inspect for rasterization or changed appearance. If only the traced SVG remains, inferred gradients cannot recover lost source detail; disclose that limitation.

## Route C: selective visual blur, only with explicit tradeoffs

SVG `feGaussianBlur` can soften patches quickly but is a rendering filter, not fewer or cleaner paths. Never blur the entire cel drawing by default: it softens lettering, outlines, and silhouette edges. If approved, isolate a shading-only group, leave sharp detail above it, and clip the filtered result to a clean surface silhouette. Expand the filter region as needed to avoid clipping. Choose `color-interpolation-filters` deliberately (default is linearRGB), and check halos and appearance on light/dark/transparent backgrounds.

Filters can be rasterized or unsupported in downstream exports. A file with no `<image>` is not proof that every export remains vector-only. Report filter usage and native/export limitations. Matching-color seam strokes solve narrow cracks, not broad posterization; they can close holes and fatten detail. Never propagate an opaque seam-fix background into transparent artwork.

## Completion gates and bounded experiment

Report the selected mode: **automatic vectorization**, **clean illustration**, or **faithful reconstruction**. Count paths/anchors and bytes, but approve based on surface continuity, preserved intentional boundaries, thin lines, holes, signage, and silhouette in same-size renders. Keep comparison artifacts and a short remaining-mismatch list. Lower mean error alone is not acceptance.

Local NGE frame experiment (1000×750, VectorCraft CLI 0.10.0): the unfiltered 64-color abutting trace had 11,682 paths, 76,800 anchors, and a 2,004,747-byte SVG. A single bilateral pass (5/20/3) followed by the same trace settings produced 10,134 paths, 65,671 anchors, and 1,780,194 bytes. The render was viewed: flat-color patches still remained. This supports preprocessing for complexity reduction on this input, **not** a claim of restored smooth gradients. Existing seam-cleaned delivery and raw traces are different variants; compare with equivalent seam treatment before judging their visual quality. This is not a completed gradient reconstruction or a general benchmark.

## Research and scope of evidence

Reviewed 2026-10-13; public docs may change.

- [OpenCV 4.13 smoothing tutorial](https://docs.opencv.org/4.13.0/d4/d13/tutorial_py_filtering.html): documented bilateral mechanism and its edge-preservation advantage over Gaussian averaging. It does not guarantee preservation of every thin/weak feature.
- [MDN linearGradient](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/linearGradient): gradient fill syntax and coordinate units. Surface segmentation and fitting above are workflow recommendations, not an automatic algorithm supplied by MDN.
- [MDN feGaussianBlur](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/feGaussianBlur): blur, filter-region clipping, and default linearRGB processing. Filter-export compatibility must be tested separately.
- [VTracer README](https://github.com/visioncortex/vtracer/blob/master/README.md), current default branch inspected: documents clustering and spline/stacked output controls. Another tracer is an optional experiment, not evidence that it reconstructs continuous gradient fills; no VTracer benchmark was run here.
- [VectorCraft source](https://github.com/storytold/vectorcraft/tree/8715130c8b11bace7e72860a3b15b893deebbb36/crates/trace/src): `smooth.rs:1–14` describes internal bilateral preprocessing; `quantize.rs:172–180` distinguishes mixed noisy palette regions from spatially separate gradient bands. Static source evidence explains why more smoothing alone need not remove banding. Runtime results above apply only to installed CLI 0.10.0.
