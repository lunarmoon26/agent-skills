#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.15"
# dependencies = ["Pillow==12.3.0", "opencv-python-headless==4.13.0.92"]
# ///
"""Write an opaque, edge-preserving PNG candidate for subsequent vector tracing."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


def prepare(source: Path, output: Path, diameter: int = 5,
            sigma_color: float = 20, sigma_space: float = 3) -> dict:
    if diameter not in {3, 5, 7, 9}:
        raise ValueError("diameter must be 3, 5, 7, or 9")
    if not all(math.isfinite(v) and v > 0 for v in (sigma_color, sigma_space)):
        raise ValueError("sigma values must be finite and positive")
    if source.resolve() == output.resolve():
        raise ValueError("output must not replace the source")
    if output.suffix.lower() != ".png":
        raise ValueError("output must be PNG")
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    with Image.open(source) as image:
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError("animated/multi-frame input is not supported")
        if image.info.get("icc_profile"):
            raise ValueError("convert ICC-tagged input to untagged sRGB before filtering")
        rgba = ImageOps.exif_transpose(image).convert("RGBA")
    if rgba.getchannel("A").getextrema() != (255, 255):
        raise ValueError("transparent input requires an alpha-aware workflow; not supported here")
    rgb = np.array(rgba.convert("RGB"))
    filtered = cv2.bilateralFilter(rgb, diameter, sigma_color, sigma_space)
    # Exclusive creation also refuses a destination created since the checks above.
    with output.open("xb") as file:
        Image.fromarray(filtered).save(file, format="PNG")
    return {"source": str(source), "output": str(output),
            "width": rgba.width, "height": rgba.height,
            "diameter": diameter, "sigma_color": sigma_color,
            "sigma_space": sigma_space,
            "note": "Pre-trace candidate, not gradient reconstruction; compare against original."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--diameter", type=int, choices=[3, 5, 7, 9], default=5)
    parser.add_argument("--sigma-color", type=float, default=20)
    parser.add_argument("--sigma-space", type=float, default=3)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.source, args.output, args.diameter,
                                 args.sigma_color, args.sigma_space)))
    except (ValueError, OSError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
