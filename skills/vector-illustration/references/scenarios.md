# Example-derived illustration scenarios

Source: [VectorCraft examples](https://github.com/storytold/vectorcraft/tree/main/examples), inspected at commit `8715130c8b11bace7e72860a3b15b893deebbb36`. These are original command-API artwork per upstream `ASSETS.md:318–335`, licensed MIT OR Apache-2.0. This skill links to them, not redistributes their artwork. Study mechanisms and composition; do not assume an example is a template that satisfies a different brief.

## Scenario map

| Example | Observed structure | Transferable workflow | Verification |
| --- | --- | --- | --- |
| `dusk-poster.vectorcraft` / `.svg` | 600×800 artboard; linear sky/lake fills, radial sun, layered mountain paths, trees/birds/stars, two type objects | Establish horizon and depth bands; use reusable silhouettes and sparse details; add typography after the landscape reads | Compare full composition and small-size hierarchy; confirm actual font availability and gradient export |
| `neon-drive.vectorcraft` | 1080×1350; compound-path cut sun, mountains, glowing type/grid, artboard clip group | Build the underlying solid geometry first; subtract sun stripes with Pathfinder; arrange grid; apply restrained live glow last | Subtraction holes, clipping bounds, text, and glow scale; disclose rasterized effects in delivery SVG |
| `ribbons.vectorcraft` | 1600×1000; three live blends with six key paths, 70/70/55 steps, artboard clipping | Create compatible start/end curves, color them, blend, adjust key paths/spine, clip overflow | Inspect curve correspondence, crossing order, and banding/aliasing at actual size—not only a downscaled preview |
| `feature-sheet.vectorcraft` | Four 700×700 boards: Pathfinder, Gradient Mesh, Repeat, Envelope; three 4×4 meshes, two radial repeats (12/24 instances), flag warp with bend 45 | Use booleans for hard cutouts; meshes for local soft shading; repeat one editable motif; envelope live content instead of manually warping every point | Export and inspect **each** artboard; keep the native live structure and distinguish it from flattened SVG geometry |
| `perspective-city.vectorcraft` | 1600×1000; two-point grid, left/right attached facade groups, repeated windows | Establish vanishing points/horizon, construct facade artwork, attach to each plane, then align repeated architectural details | Convergence, verticals, window rhythm, plane seams, and editability after native reopen |

Observed source sites: dusk gradient/silhouette/type data at `examples/dusk-poster.vectorcraft:61,3866,4036–4340,4491,6504`; neon glow/clip data at `examples/neon-drive.vectorcraft:10716,11260,11599,13162`; blend structure at `examples/ribbons.vectorcraft:368–1062`; mesh/repeat/envelope data at `examples/feature-sheet.vectorcraft:1311,2105,2899,3923,4065,6084`; perspective data at `examples/perspective-city.vectorcraft:3345,7201,8151`. Native JSON is evidence for the examples' structure, not a schema to hand-author.

## Commands to discover for each mechanism

Use the installed `vectorcraft-cli commands` catalogue. Read parameter ranges, target IDs, defaults, and returned IDs before composing a run. These IDs were confirmed in installed `0.10.0`; they are not a frozen API.

| Mechanism | Entry points | Important behavior |
| --- | --- | --- |
| Shapes/custom curves | `shape.rectangle`, `shape.ellipse`, `path.create` | `path.create` accepts SVG `d` or anchors with in/out handles; use few purposeful anchors, not a vertex at every pixel |
| Gradients | `paint.setFill` | `gradient` supports kind/stops/angle and document-space start/end; target explicit `ids` to avoid unintentionally changing other art |
| Text/live appearance | `text.create`, `effect.apply` | Discover fonts and effect schemas; `stylize.outerGlow` parameters come from the effect registry, not the generic effect command |
| Hard cutouts | `object.pathfinder.unite`, `object.pathfinder.minusFront`, `object.pathfinder.intersect`, `object.pathfinder.exclude` | Selection paint order determines subtraction; inspect shapes and selection first |
| Clip group | `object.clippingMask.make` | The topmost selected path/compound path/text clips the others and loses its paint; do not accidentally use artwork as the clipping boundary |
| Live ribbons | `object.blend.make`, `object.blend.options`, `object.blend.replaceSpine` | Preserve key objects; tune steps/correspondence before increasing density to hide errors |
| Mandalas/motifs | `object.repeat.radial`, `object.repeat.grid`, `object.repeat.mirror` | Keep one intentional seed motif; inspect spacing, instance count, and repeat center |
| Envelope | `object.envelope.makeWithWarp`, `object.envelope.makeWithMesh` | Distort editable content; do not confuse an envelope mesh with a color gradient mesh |
| Soft local shading | `object.mesh.create`, `object.mesh.setPointColor` | Converts filled paths to meshes; inspect bounds and corner colors before adding control points |
| Perspective | `perspective.grid.preset`, `perspective.grid.set`, `perspective.attach` | Attach explicit object IDs to left/right/ground planes; preserve plane attachments in the native master |

Schema owners upstream: `crates/engine/src/cmd/{create,paint,pathops,object,live,patterncmds,distortcmds,effectcmd}.rs`; effect-specific schemas in `crates/effects/src/lib.rs`. For persistent iteration, use native MCP's focused object reads instead of repeatedly dumping a large catalogue/document.

## How to learn from a sample

1. Open the sample with `info`, then inspect a sliced tree in `run` or native MCP.
2. Find one representative group/object and read its geometry/appearance. Trace the command that creates that mechanism; do not copy hundreds of native JSON fields.
3. Reproduce a small independent variant through engine commands. Save native, export SVG/PNG, reopen native, and confirm the blend/repeat/mesh/envelope is still live.
4. Compose original artwork for the user's brief. The poster examples' styling is not a default: a cel-animation reconstruction needs hard shaded patches, not neon glows or a mesh everywhere.
5. Inspect all requested artboards and delivery formats, not just the first PNG.

## Validation scope

On 2026-10-13, installed CLI `0.10.0` opened and exported all five native examples to PNG without reported import/export warnings; their renders, including all four feature-sheet artboards, were visually inspected. This establishes a bounded smoke test, not professional fidelity, font parity on other hosts, or browser equivalence. The half-scale ribbon preview shows dense line texture/aliasing: assess blend density at delivery size. Live mechanism tests in this skill exercise independently created blends, repeats, meshes, envelopes, and perspective; they do not establish identical pixels to upstream screenshots.
