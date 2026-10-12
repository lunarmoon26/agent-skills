#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.15"
# dependencies = ["Pillow==12.3.0"]
# ///
"""Same-size raster diagnostics for iterative vector reconstruction."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageOps, ImageStat


def load(path: Path) -> Image.Image:
    with Image.open(path) as image:
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError(f"animated/multi-frame input is not supported: {path}")
        return ImageOps.exif_transpose(image).convert("RGBA")


def compare(reference: Path, rendered: Path, output_dir: Path, background: str, overwrite: bool = False) -> dict:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", background):
        raise ValueError("background must be #RRGGBB")
    original, candidate = load(reference), load(rendered)
    if original.size != candidate.size:
        raise ValueError(f"pixel dimensions differ: {original.size} vs {candidate.size}; correct the export, do not stretch it")
    destinations = {name: output_dir / name for name in (
        "side-by-side.png", "overlay.png", "difference.png", "report.json",
    )}
    for destination in destinations.values():
        for source in (reference, rendered):
            if destination.resolve() == source.resolve() or (destination.exists() and destination.samefile(source)):
                raise ValueError(f"refusing to replace an input: {destination}")
        if destination.is_symlink():
            raise ValueError(f"refusing a symlink output: {destination}")
        if destination.exists() and not overwrite:
            raise FileExistsError(f"output exists; use a new directory or --overwrite: {destination}")
    paths = list(destinations.values())
    for index, path in enumerate(paths):
        for other in paths[:index]:
            if path.resolve() == other.resolve() or (path.exists() and other.exists() and path.samefile(other)):
                raise ValueError(f"output paths alias each other: {path} and {other}")

    def flatten(image: Image.Image) -> Image.Image:
        canvas = Image.new("RGBA", image.size, background)
        canvas.alpha_composite(image)
        return canvas.convert("RGB")

    left, right = flatten(original), flatten(candidate)
    difference = ImageChops.difference(left, right)
    channel_mae = ImageStat.Stat(difference).mean
    alpha_mae = ImageStat.Stat(ImageChops.difference(original.getchannel("A"), candidate.getchannel("A"))).mean[0]
    side_by_side = Image.new("RGB", (left.width * 2, left.height))
    side_by_side.paste(left, (0, 0))
    side_by_side.paste(right, (left.width, 0))
    report = {
        "reference": str(reference), "rendered": str(rendered),
        "width": left.width, "height": left.height, "background": background,
        "rgb_mae": sum(channel_mae) / 3, "rgb_channel_mae": channel_mae, "alpha_mae": alpha_mae,
        "metric_note": "Absolute 0–255 channel error, not a perceptual similarity score; no resizing or color-profile conversion.",
        "outputs": {name: str(path) for name, path in destinations.items()},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    side_by_side.save(destinations["side-by-side.png"])
    Image.blend(left, right, 0.5).save(destinations["overlay.png"])
    difference.save(destinations["difference.png"])
    destinations["report.json"].write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("rendered", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--background", default="#ffffff")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        report = compare(args.reference, args.rendered, args.output_dir, args.background, args.overwrite)
    except (OSError, ValueError) as error:
        parser.exit(2, f"compare: {error}\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
