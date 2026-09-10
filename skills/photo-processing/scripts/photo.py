#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.15"
# dependencies = [
#   "Pillow==12.3.0",
# ]
# ///
# pyright: reportMissingImports=false
"""Non-destructive image resizing, transparency, icon, and sprite-sheet tools.

Run with the pinned Pillow version supplied by uv:
    uv run --script photo.py --help
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import deque
from collections.abc import Callable, Iterable
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

FORMAT_ALIASES = {
    "avif": "AVIF",
    "bmp": "BMP",
    "gif": "GIF",
    "ico": "ICO",
    "jpeg": "JPEG",
    "jpg": "JPEG",
    "png": "PNG",
    "tif": "TIFF",
    "tiff": "TIFF",
    "webp": "WEBP",
}
FORMAT_EXTENSIONS = {
    "AVIF": ".avif",
    "BMP": ".bmp",
    "GIF": ".gif",
    "ICO": ".ico",
    "JPEG": ".jpg",
    "PNG": ".png",
    "TIFF": ".tiff",
    "WEBP": ".webp",
}
ANCHORS = {
    "north-west": (0.0, 0.0),
    "north": (0.5, 0.0),
    "north-east": (1.0, 0.0),
    "west": (0.0, 0.5),
    "center": (0.5, 0.5),
    "east": (1.0, 0.5),
    "south-west": (0.0, 1.0),
    "south": (0.5, 1.0),
    "south-east": (1.0, 1.0),
}


def positive_int(value: str) -> int:
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def nonnegative_int(value: str) -> int:
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return result


def channel_value(value: str) -> int:
    result = int(value)
    if not 0 <= result <= 255:
        raise argparse.ArgumentTypeError("must be between 0 and 255")
    return result


def nonnegative_float(value: str) -> float:
    result = float(value)
    if result < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return result


def parse_color(value: str) -> tuple[int, int, int, int]:
    raw = value.strip().removeprefix("#")
    if "," in raw:
        channels = [item.strip() for item in raw.split(",")]
        if len(channels) not in (3, 4):
            raise argparse.ArgumentTypeError("comma-separated colors need 3 or 4 channels")
        try:
            parsed = [int(channel) for channel in channels]
        except ValueError as error:
            raise argparse.ArgumentTypeError("color channels must be integers") from error
    elif len(raw) in (3, 4):
        try:
            parsed = [int(channel * 2, 16) for channel in raw]
        except ValueError as error:
            raise argparse.ArgumentTypeError("invalid hexadecimal color") from error
    elif len(raw) in (6, 8):
        try:
            parsed = [int(raw[index : index + 2], 16) for index in range(0, len(raw), 2)]
        except ValueError as error:
            raise argparse.ArgumentTypeError("invalid hexadecimal color") from error
    else:
        raise argparse.ArgumentTypeError("use #RRGGBB, #RRGGBBAA, or R,G,B[,A]")

    if any(channel < 0 or channel > 255 for channel in parsed):
        raise argparse.ArgumentTypeError("color channels must be between 0 and 255")
    return tuple(parsed + [255] if len(parsed) == 3 else parsed)  # type: ignore[return-value]


def parse_format(value: str) -> str:
    image_format = FORMAT_ALIASES.get(value.lower().removeprefix("."))
    if image_format is None:
        supported = ", ".join(FORMAT_ALIASES)
        raise argparse.ArgumentTypeError(f"unsupported format {value!r}; use one of: {supported}")
    return image_format


def format_from_path(path: Path) -> str:
    return parse_format(path.suffix)


def parse_format_list(value: str) -> list[str]:
    return [parse_format(item) for item in value.split(",") if item.strip()]


def collect_sources(inputs: Iterable[Path], recursive: bool) -> list[Path]:
    sources: list[Path] = []
    for input_path in inputs:
        if not input_path.exists():
            raise FileNotFoundError(input_path)
        if input_path.is_file():
            sources.append(input_path)
            continue
        files = input_path.rglob("*") if recursive else input_path.glob("*")
        sources.extend(path for path in files if path.is_file())
    if not sources:
        raise ValueError("no input image files found")
    return sorted(sources)


def load_image(path: Path, first_frame: bool) -> Image.Image:
    with Image.open(path) as opened:
        frame_count = getattr(opened, "n_frames", 1)
        if frame_count > 1 and not first_frame:
            raise ValueError(f"{path} has {frame_count} frames; pass --first-frame to process only its first frame")
        return ImageOps.exif_transpose(opened).copy()


def verify_destination(source: Path, destination: Path, overwrite: bool) -> None:
    if destination.exists() and not overwrite:
        raise FileExistsError(f"output exists; pass --overwrite to replace it: {destination}")
    if source.resolve() == destination.resolve() and not overwrite:
        raise FileExistsError(f"refusing to overwrite the input without --overwrite: {source}")


def flatten(image: Image.Image, background: tuple[int, int, int, int]) -> Image.Image:
    canvas = Image.new("RGBA", image.size, background)
    canvas.alpha_composite(image.convert("RGBA"))
    return canvas.convert("RGB")


def prepare_for_save(image: Image.Image, image_format: str, background: tuple[int, int, int, int]) -> Image.Image:
    if image_format in {"JPEG", "BMP"}:
        return flatten(image, background)
    if image_format == "GIF":
        return image.convert("RGBA").convert("P", palette=Image.Palette.ADAPTIVE)
    if image_format == "ICO":
        return image.convert("RGBA")
    if image.mode not in {"RGB", "RGBA", "L", "LA"}:
        return image.convert("RGBA")
    return image


def save_image(
    image: Image.Image,
    destination: Path,
    image_format: str,
    quality: int,
    background: tuple[int, int, int, int],
    ico_sizes: list[int] | None = None,
) -> None:
    Image.init()
    if image_format not in Image.SAVE:
        raise ValueError(f"Pillow was installed without a writer for {image_format}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    output = prepare_for_save(image, image_format, background)
    output.info.clear()
    save_args: dict[str, object] = {}
    if image_format == "PNG":
        save_args["optimize"] = True
    elif image_format == "JPEG":
        save_args.update(quality=quality, optimize=True, progressive=True)
    elif image_format in {"WEBP", "AVIF"}:
        save_args["quality"] = quality
    elif image_format == "ICO" and ico_sizes:
        save_args["sizes"] = [(size, size) for size in ico_sizes]
    output.save(destination, image_format, **save_args)


def anchor_offset(container: tuple[int, int], content: tuple[int, int], anchor: str) -> tuple[int, int]:
    horizontal, vertical = ANCHORS[anchor]
    return (
        round((container[0] - content[0]) * horizontal),
        round((container[1] - content[1]) * vertical),
    )


def resize_image(
    image: Image.Image,
    width: int | None,
    height: int | None,
    fit: str,
    anchor: str,
    pad: bool,
    background: tuple[int, int, int, int],
) -> Image.Image:
    if width is None and height is None:
        raise ValueError("provide --width, --height, or both")
    if pad and (width is None or height is None):
        raise ValueError("--pad requires both --width and --height")
    source_width, source_height = image.size
    if width is None:
        width = max(1, round(source_width * height / source_height))
    if height is None:
        height = max(1, round(source_height * width / source_width))

    if fit == "fill":
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
    elif fit == "cover":
        resized = ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS, centering=ANCHORS[anchor])
    else:
        scale = min(width / source_width, height / source_height)
        if fit == "inside":
            scale = min(1.0, scale)
        resized = image.resize(
            (max(1, round(source_width * scale)), max(1, round(source_height * scale))),
            Image.Resampling.LANCZOS,
        )

    if not pad:
        return resized
    canvas = Image.new("RGBA", (width, height), background)
    canvas.alpha_composite(resized.convert("RGBA"), anchor_offset(canvas.size, resized.size, anchor))
    return canvas


def destination_for_resize(source: Path, args: argparse.Namespace, image_format: str) -> Path:
    if args.output is not None:
        return args.output
    output_dir = args.output_dir or source.parent
    return output_dir / f"{source.stem}{args.suffix}{FORMAT_EXTENSIONS[image_format]}"


def command_resize(args: argparse.Namespace) -> None:
    sources = collect_sources(args.inputs, args.recursive)
    if args.output is not None:
        output_format = format_from_path(args.output)
        if args.formats and (len(args.formats) != 1 or args.formats[0] != output_format):
            raise ValueError("--format must match the --output file extension")
        formats = [output_format]
    else:
        formats = args.formats or [format_from_path(source) for source in sources]
    if args.output is not None and (len(sources) != 1 or len(formats) != 1):
        raise ValueError("--output requires exactly one source and one output format")
    for source in sources:
        image = load_image(source, args.first_frame)
        source_formats = formats if args.output is not None or args.formats else [format_from_path(source)]
        for image_format in source_formats:
            destination = destination_for_resize(source, args, image_format)
            verify_destination(source, destination, args.overwrite)
            resized = resize_image(
                image,
                args.width,
                args.height,
                args.fit,
                args.anchor,
                args.pad,
                args.background,
            )
            save_image(resized, destination, image_format, args.quality, args.background, args.ico_sizes)
            print(f"{source} -> {destination} ({resized.width}x{resized.height}, {image_format})")


def replace_alpha(image: Image.Image, alpha_values: Iterable[int]) -> Image.Image:
    output = image.convert("RGBA")
    alpha = Image.new("L", output.size)
    alpha.putdata(alpha_values)
    output.putalpha(alpha)
    return output


def key_color(
    image: Image.Image,
    color: tuple[int, int, int, int],
    tolerance: float,
    feather: float,
) -> Image.Image:
    if tolerance > math.sqrt(3 * 255**2):
        raise ValueError("--tolerance cannot exceed 441.67")
    source = image.convert("RGBA")
    red, green, blue, _ = color
    alpha_values: list[int] = []
    for pixel_red, pixel_green, pixel_blue, pixel_alpha in source.get_flattened_data():
        distance = math.dist((pixel_red, pixel_green, pixel_blue), (red, green, blue))
        if distance <= tolerance:
            multiplier = 0.0
        elif feather and distance < tolerance + feather:
            multiplier = (distance - tolerance) / feather
        else:
            multiplier = 1.0
        alpha_values.append(round(pixel_alpha * multiplier))
    return replace_alpha(source, alpha_values)


def flood_fill_color(
    image: Image.Image,
    seed_x: int,
    seed_y: int,
    color: tuple[int, int, int, int],
    tolerance: int,
    alpha_mode: str,
    connectivity: int,
) -> tuple[Image.Image, int]:
    """Replace the seed-connected color region and return its pixel count.

    Matching is always measured against the original seed color, preventing
    the gradual color drift that occurs when each neighbor is compared with
    the previously visited pixel.
    """
    source = image.convert("RGBA")
    width, height = source.size
    if not 0 <= seed_x < width or not 0 <= seed_y < height:
        raise ValueError(f"seed ({seed_x}, {seed_y}) is outside the {width}x{height} image")
    if alpha_mode not in {"ignore", "match"}:
        raise ValueError("--alpha-mode must be ignore or match")
    if connectivity not in {4, 8}:
        raise ValueError("--connectivity must be 4 or 8")

    pixels = source.load()
    seed = pixels[seed_x, seed_y]
    channel_count = 4 if alpha_mode == "match" else 3
    selected = bytearray(width * height)
    queue: deque[int] = deque()

    def matches(pixel: tuple[int, int, int, int]) -> bool:
        return all(abs(pixel[channel] - seed[channel]) <= tolerance for channel in range(channel_count))

    def enqueue(x: int, y: int) -> bool:
        index = y * width + x
        if selected[index] or not matches(pixels[x, y]):
            return False
        selected[index] = 1
        pixels[x, y] = color
        queue.append(index)
        return True

    enqueue(seed_x, seed_y)
    selected_count = 1
    while queue:
        index = queue.popleft()
        x = index % width
        y = index // width
        for offset_y in (-1, 0, 1):
            next_y = y + offset_y
            if not 0 <= next_y < height:
                continue
            for offset_x in (-1, 0, 1):
                if offset_x == 0 and offset_y == 0:
                    continue
                if connectivity == 4 and offset_x != 0 and offset_y != 0:
                    continue
                next_x = x + offset_x
                if 0 <= next_x < width and enqueue(next_x, next_y):
                    selected_count += 1

    return source, selected_count


def srgb_to_linear(channel: int) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance_alpha(
    image: Image.Image,
    start: int,
    end: int,
    gamma: float,
    blur: float,
    alpha_mode: str,
    alpha_floor: int,
) -> Image.Image:
    if end <= start:
        raise ValueError("--end must be greater than --start")
    if gamma <= 0:
        raise ValueError("--gamma must be positive")
    source = image.convert("RGBA")
    output_pixels: list[tuple[int, int, int, int]] = []
    for red, green, blue, source_alpha in source.get_flattened_data():
        if alpha_mode == "replace":
            brightness = round(0.2126 * red + 0.7152 * green + 0.0722 * blue)
        else:
            brightness = round(
                255
                * (
                    0.2126 * srgb_to_linear(red)
                    + 0.7152 * srgb_to_linear(green)
                    + 0.0722 * srgb_to_linear(blue)
                )
            )
        normalized = min(1.0, max(0.0, (brightness - start) / (end - start)))
        alpha = round(255 * normalized**gamma)
        if alpha <= alpha_floor:
            alpha = 0
        if alpha_mode == "multiply":
            alpha = round(source_alpha * alpha / 255)
            output_pixels.append((red, green, blue, alpha))
        elif alpha == 0 or brightness == 0:
            output_pixels.append((0, 0, 0, 0))
        else:
            scale = 255 / brightness
            output_pixels.append(
                (
                    min(255, round(red * scale)),
                    min(255, round(green * scale)),
                    min(255, round(blue * scale)),
                    alpha,
                )
            )
    output = Image.new("RGBA", source.size)
    output.putdata(output_pixels)
    if blur:
        output.putalpha(output.getchannel("A").filter(ImageFilter.GaussianBlur(blur)))
    return output


def mask_image(image: Image.Image, color: tuple[int, int, int, int], alpha_source: str, opacity: float) -> Image.Image:
    source = image.convert("RGBA")
    original_alpha = source.getchannel("A")
    if alpha_source == "alpha":
        alpha = original_alpha
    else:
        luminance = source.convert("L")
        if alpha_source == "inverse-luminance":
            luminance = ImageOps.invert(luminance)
        alpha = Image.new("L", source.size)
        alpha.putdata(
            [round(value * existing / 255) for value, existing in zip(luminance.get_flattened_data(), original_alpha.get_flattened_data())]
        )
    color_alpha = color[3] / 255 * opacity
    if color_alpha != 1:
        alpha = alpha.point(lambda value: round(value * color_alpha))
    output = Image.new("RGBA", source.size, color[:3] + (0,))
    output.putalpha(alpha)
    return output


def trim_image(image: Image.Image, padding: int, square: bool) -> Image.Image:
    source = image.convert("RGBA")
    bounds = source.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("image has no visible pixels after alpha processing")
    cropped = source.crop(bounds)
    width, height = cropped.size
    if square:
        side = max(width, height) + padding * 2
        canvas_size = (side, side)
    else:
        canvas_size = (width + padding * 2, height + padding * 2)
    output = Image.new("RGBA", canvas_size)
    output.alpha_composite(cropped, anchor_offset(canvas_size, cropped.size, "center"))
    return output


def destination_for_transform(source: Path, args: argparse.Namespace, default_format: str = "PNG") -> tuple[Path, str]:
    if args.output is not None:
        image_format = format_from_path(args.output)
        return args.output, image_format
    image_format = args.format or default_format
    output_dir = args.output_dir or source.parent
    return output_dir / f"{source.stem}{args.suffix}{FORMAT_EXTENSIONS[image_format]}", image_format


def process_transform(
    args: argparse.Namespace,
    transform: Callable[[Image.Image], Image.Image],
    default_format: str = "PNG",
) -> None:
    sources = collect_sources(args.inputs, args.recursive)
    if args.output is not None and len(sources) != 1:
        raise ValueError("--output requires exactly one source")
    for source in sources:
        destination, image_format = destination_for_transform(source, args, default_format)
        verify_destination(source, destination, args.overwrite)
        output = transform(load_image(source, args.first_frame))
        save_image(output, destination, image_format, args.quality, args.background, args.ico_sizes)
        print(f"{source} -> {destination} ({output.width}x{output.height}, {image_format})")


def command_key_color(args: argparse.Namespace) -> None:
    process_transform(args, lambda image: key_color(image, args.color, args.tolerance, args.feather))


def command_flood_fill(args: argparse.Namespace) -> None:
    sources = collect_sources(args.inputs, args.recursive)
    if args.output is not None and len(sources) != 1:
        raise ValueError("--output requires exactly one source")
    for source in sources:
        destination, image_format = destination_for_transform(source, args)
        verify_destination(source, destination, args.overwrite)
        output, selected_count = flood_fill_color(
            load_image(source, args.first_frame),
            args.x,
            args.y,
            args.color,
            args.tolerance,
            args.alpha_mode,
            args.connectivity,
        )
        save_image(output, destination, image_format, args.quality, args.background, args.ico_sizes)
        print(
            f"{source} -> {destination} ({output.width}x{output.height}, {image_format}; "
            f"filled {selected_count} pixels)"
        )


def command_key_luminance(args: argparse.Namespace) -> None:
    process_transform(
        args,
        lambda image: luminance_alpha(
            image,
            args.start,
            args.end,
            args.gamma,
            args.blur,
            args.alpha_mode,
            args.alpha_floor,
        ),
    )


def command_mask(args: argparse.Namespace) -> None:
    process_transform(args, lambda image: mask_image(image, args.color, args.alpha_source, args.opacity))


def command_trim(args: argparse.Namespace) -> None:
    process_transform(args, lambda image: trim_image(image, args.padding, args.square))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot make an asset name from {value!r}")
    return slug


def split_labels(raw_labels: str | None, count: int) -> list[str]:
    if raw_labels is None:
        return []
    labels = [slugify(label) for label in raw_labels.split(",")]
    if len(labels) != count:
        raise ValueError(f"--labels needs exactly {count} comma-separated names")
    if len(set(labels)) != len(labels):
        raise ValueError("--labels must be unique after normalizing to asset names")
    return labels


def grid_cell_size(image: Image.Image, args: argparse.Namespace) -> tuple[int, int]:
    width = args.cell_width
    height = args.cell_height
    if width is None:
        available = image.width - args.origin_x - args.margin_right - args.gap_x * (args.columns - 1)
        width, remainder = divmod(available, args.columns)
        if remainder:
            raise ValueError("image width does not divide into an exact grid; pass --cell-width")
    if height is None:
        available = image.height - args.origin_y - args.margin_bottom - args.gap_y * (args.rows - 1)
        height, remainder = divmod(available, args.rows)
        if remainder:
            raise ValueError("image height does not divide into an exact grid; pass --cell-height")
    if width <= 0 or height <= 0:
        raise ValueError("the calculated cell size must be positive")
    final_right = args.origin_x + width * args.columns + args.gap_x * (args.columns - 1)
    final_bottom = args.origin_y + height * args.rows + args.gap_y * (args.rows - 1)
    if final_right > image.width or final_bottom > image.height:
        raise ValueError("the grid extends past the input image; adjust origin, cells, or gaps")
    return width, height


def write_sprite_css(
    path: Path,
    class_name: str,
    image_url: str,
    image_size: tuple[int, int],
    cell_size: tuple[int, int],
    cells: list[dict[str, object]],
    scale: float,
) -> None:
    width = round(cell_size[0] * scale, 4)
    height = round(cell_size[1] * scale, 4)
    background_width = round(image_size[0] * scale, 4)
    background_height = round(image_size[1] * scale, 4)
    lines = [
        f".{class_name} {{",
        "  display: inline-block;",
        f'  background-image: url("{image_url}");',
        "  background-repeat: no-repeat;",
        f"  width: {width}px;",
        f"  height: {height}px;",
        f"  background-size: {background_width}px {background_height}px;",
        "}",
        "",
    ]
    for cell in cells:
        x, y, _, _ = cell["sourceRect"]  # type: ignore[misc]
        name = cell["name"]
        lines.extend(
            [
                f".{class_name}--{name} {{",
                f"  background-position: {-round(x * scale, 4)}px {-round(y * scale, 4)}px;",
                "}",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def command_sprite_grid(args: argparse.Namespace) -> None:
    source = load_image(args.input, args.first_frame)
    cell_width, cell_height = grid_cell_size(source, args)
    count = args.columns * args.rows
    labels = split_labels(args.labels, count)
    output_dir = args.output_dir or args.input.parent / f"{args.input.stem}-sprites"
    metadata_path = args.metadata or output_dir / f"{slugify(args.prefix)}.json"
    cells: list[dict[str, object]] = []
    preview = source.convert("RGBA").copy() if args.preview else None
    draw = ImageDraw.Draw(preview) if preview else None

    for row in range(args.rows):
        for column in range(args.columns):
            index = row * args.columns + column
            name = labels[index] if args.labels else f"r{row:02d}-c{column:02d}"
            x = args.origin_x + column * (cell_width + args.gap_x)
            y = args.origin_y + row * (cell_height + args.gap_y)
            rect = (x, y, cell_width, cell_height)
            crop = source.crop((x, y, x + cell_width, y + cell_height))
            if args.trim:
                crop = trim_image(crop, args.padding, args.square)
            destination = output_dir / f"{slugify(args.prefix)}-{name}{FORMAT_EXTENSIONS[args.format]}"
            verify_destination(args.input, destination, args.overwrite)
            save_image(crop, destination, args.format, args.quality, args.background, args.ico_sizes)
            cells.append(
                {
                    "name": name,
                    "row": row,
                    "column": column,
                    "sourceRect": rect,
                    "output": destination.name,
                    "outputSize": crop.size,
                    "backgroundPosition": [-round(x * args.css_scale, 4), -round(y * args.css_scale, 4)],
                }
            )
            if draw:
                draw.rectangle((x, y, x + cell_width - 1, y + cell_height - 1), outline="#ff3b30", width=2)
                draw.text((x + 4, y + 4), name, fill="#ffdc00", stroke_width=1, stroke_fill="#000000")
            print(f"{args.input} [{row},{column}] -> {destination}")

    metadata = {
        "source": str(args.input),
        "sourceSize": source.size,
        "grid": {
            "columns": args.columns,
            "rows": args.rows,
            "origin": [args.origin_x, args.origin_y],
            "cellSize": [cell_width, cell_height],
            "gap": [args.gap_x, args.gap_y],
            "cssScale": args.css_scale,
        },
        "cells": cells,
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"metadata -> {metadata_path}")
    if args.css:
        write_sprite_css(
            args.css,
            slugify(args.css_class),
            args.image_url or args.input.name,
            source.size,
            (cell_width, cell_height),
            cells,
            args.css_scale,
        )
        print(f"css -> {args.css}")
    if preview and args.preview:
        save_image(preview, args.preview, format_from_path(args.preview), args.quality, args.background)
        print(f"preview -> {args.preview}")


def command_inspect(args: argparse.Namespace) -> None:
    for source in collect_sources(args.inputs, args.recursive):
        with Image.open(source) as image:
            print(
                json.dumps(
                    {
                        "path": str(source),
                        "format": image.format,
                        "size": image.size,
                        "mode": image.mode,
                        "frames": getattr(image, "n_frames", 1),
                        "hasAlpha": "A" in image.getbands() or "transparency" in image.info,
                    }
                )
            )


def add_common_input(parser: argparse.ArgumentParser, multiple: bool = True) -> None:
    parser.add_argument("inputs" if multiple else "input", nargs="+" if multiple else None, type=Path, help="Image file(s), or directories of image files.")
    if multiple:
        parser.add_argument("--recursive", action="store_true", help="Include files below input directories.")
    parser.add_argument("--first-frame", action="store_true", help="Process only the first frame of animated inputs.")


def add_output_options(parser: argparse.ArgumentParser, default_suffix: str, include_ico: bool = True) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--output", type=Path, help="Output file. Only valid for one input.")
    group.add_argument("--output-dir", type=Path, help="Directory for generated files.")
    parser.add_argument("--suffix", default=default_suffix, help=f"Filename suffix when generating paths. Default: {default_suffix}")
    parser.add_argument("--format", type=parse_format, help="Output format when no --output is given. Default: PNG.")
    parser.add_argument("--quality", type=positive_int, default=90, help="JPEG, WebP, and AVIF quality. Default: 90.")
    parser.add_argument("--background", type=parse_color, default=(255, 255, 255, 255), help="Background used when writing formats without alpha. Default: white.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output.")
    if include_ico:
        parser.add_argument("--ico-sizes", default="16,32,48,64,128,256", help="Comma-separated square sizes for ICO output.")


def parse_ico_sizes(value: str) -> list[int]:
    sizes = [positive_int(item) for item in value.split(",")]
    if len(set(sizes)) != len(sizes):
        raise ValueError("--ico-sizes cannot contain duplicates")
    return sizes


def normalize_ico_sizes(args: argparse.Namespace) -> None:
    if hasattr(args, "ico_sizes") and isinstance(args.ico_sizes, str):
        args.ico_sizes = parse_ico_sizes(args.ico_sizes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Print image dimensions, mode, format, and frame count as JSON.")
    add_common_input(inspect_parser)
    inspect_parser.set_defaults(handler=command_inspect)

    resize_parser = subparsers.add_parser("resize", help="Resize, convert, pad, and batch-export static images.")
    add_common_input(resize_parser)
    resize_parser.add_argument("--width", type=positive_int, help="Target width in pixels.")
    resize_parser.add_argument("--height", type=positive_int, help="Target height in pixels.")
    resize_parser.add_argument("--fit", choices=("contain", "cover", "fill", "inside"), default="contain", help="contain fits within bounds, cover crops to fill, fill distorts, inside avoids upscaling.")
    resize_parser.add_argument("--anchor", choices=ANCHORS, default="center", help="Crop or padding alignment. Default: center.")
    resize_parser.add_argument("--pad", action="store_true", help="Pad a contain/inside resize to the exact width and height.")
    output_group = resize_parser.add_mutually_exclusive_group()
    output_group.add_argument("--output", type=Path, help="Output file. Only valid for one input and format.")
    output_group.add_argument("--output-dir", type=Path, help="Directory for generated files.")
    resize_parser.add_argument("--suffix", default="-resized", help="Filename suffix when generating paths. Default: -resized.")
    resize_parser.add_argument("--format", dest="formats", type=parse_format_list, help="Comma-separated output formats, such as png,webp,jpg. Default: input format.")
    resize_parser.add_argument("--quality", type=positive_int, default=90, help="JPEG, WebP, and AVIF quality. Default: 90.")
    resize_parser.add_argument("--background", type=parse_color, default=(255, 255, 255, 255), help="Background used when writing formats without alpha. Default: white.")
    resize_parser.add_argument("--ico-sizes", default="16,32,48,64,128,256", help="Comma-separated square sizes for ICO output.")
    resize_parser.add_argument("--overwrite", action="store_true", help="Replace existing output files.")
    resize_parser.set_defaults(handler=command_resize)

    key_color_parser = subparsers.add_parser("key-color", help="Make a chosen background color transparent.")
    add_common_input(key_color_parser)
    key_color_parser.add_argument("--color", type=parse_color, required=True, help="Background color to remove, such as #000000 or 0,0,0.")
    key_color_parser.add_argument("--tolerance", type=nonnegative_float, default=0, help="RGB distance removed completely. Default: 0.")
    key_color_parser.add_argument("--feather", type=nonnegative_float, default=0, help="Additional RGB-distance band faded to opaque. Default: 0.")
    add_output_options(key_color_parser, "-keyed")
    key_color_parser.set_defaults(handler=command_key_color)

    flood_fill_parser = subparsers.add_parser(
        "flood-fill",
        help="Replace a contiguous seed-connected color region, similar to Magic Wand with Contiguous enabled.",
    )
    add_common_input(flood_fill_parser)
    flood_fill_parser.add_argument("--x", type=nonnegative_int, required=True, help="Seed X coordinate in source pixels.")
    flood_fill_parser.add_argument("--y", type=nonnegative_int, required=True, help="Seed Y coordinate in source pixels.")
    flood_fill_parser.add_argument(
        "--color",
        type=parse_color,
        required=True,
        help="Replacement RGBA color, such as #ff00ffff or #00000000 for transparent.",
    )
    flood_fill_parser.add_argument(
        "--tolerance",
        type=channel_value,
        default=0,
        help="Allowed difference above or below each sampled channel, from 0 to 255. Default: 0.",
    )
    flood_fill_parser.add_argument(
        "--alpha-mode",
        choices=("match", "ignore"),
        default="match",
        help="match includes alpha in tolerance checks; ignore compares RGB only. Default: match.",
    )
    flood_fill_parser.add_argument(
        "--connectivity",
        type=int,
        choices=(4, 8),
        default=8,
        help="Treat edge-sharing pixels (4) or edge/diagonal-sharing pixels (8) as contiguous. Default: 8.",
    )
    add_output_options(flood_fill_parser, "-filled")
    flood_fill_parser.set_defaults(handler=command_flood_fill)

    key_luminance_parser = subparsers.add_parser("key-luminance", help="Derive transparency from perceived brightness; useful for dark backdrops.")
    add_common_input(key_luminance_parser)
    key_luminance_parser.add_argument("--start", type=nonnegative_int, default=0, help="Brightness at or below which alpha is zero. Default: 0.")
    key_luminance_parser.add_argument("--end", type=positive_int, default=255, help="Brightness at or above which alpha is full. Default: 255.")
    key_luminance_parser.add_argument("--gamma", type=float, default=1.0, help="Alpha ramp gamma. Default: 1.")
    key_luminance_parser.add_argument("--blur", type=nonnegative_float, default=0, help="Gaussian blur radius for the alpha matte. Default: 0.")
    key_luminance_parser.add_argument(
        "--alpha-mode",
        choices=("multiply", "replace"),
        default="multiply",
        help=(
            "multiply preserves and scales existing alpha; replace ignores existing alpha, derives alpha from "
            "sRGB luminance, and normalizes RGB to avoid double attenuation. Default: multiply."
        ),
    )
    key_luminance_parser.add_argument(
        "--alpha-floor",
        type=nonnegative_int,
        default=0,
        help="Set calculated alpha values at or below this threshold to zero. Default: 0.",
    )
    add_output_options(key_luminance_parser, "-luma-keyed")
    key_luminance_parser.set_defaults(handler=command_key_luminance)

    mask_parser = subparsers.add_parser("mask", help="Render an image silhouette in one solid color.")
    add_common_input(mask_parser)
    mask_parser.add_argument("--color", type=parse_color, required=True, help="Output color, such as #72ffff.")
    mask_parser.add_argument("--alpha-source", choices=("alpha", "luminance", "inverse-luminance"), default="alpha", help="Use existing transparency, brightness, or inverted brightness as the icon mask.")
    mask_parser.add_argument("--opacity", type=float, default=1.0, help="Final opacity from 0 to 1. Default: 1.")
    add_output_options(mask_parser, "-masked")
    mask_parser.set_defaults(handler=command_mask)

    trim_parser = subparsers.add_parser("trim", help="Crop transparent margins and optionally create padded square icons.")
    add_common_input(trim_parser)
    trim_parser.add_argument("--padding", type=nonnegative_int, default=0, help="Transparent padding after trimming. Default: 0.")
    trim_parser.add_argument("--square", action="store_true", help="Center the trimmed result in a square canvas.")
    add_output_options(trim_parser, "-trimmed")
    trim_parser.set_defaults(handler=command_trim)

    sprite_parser = subparsers.add_parser("sprite-grid", help="Cut a regular icon grid and emit crop offsets, metadata, CSS, and a guide image.")
    add_common_input(sprite_parser, multiple=False)
    sprite_parser.add_argument("--columns", type=positive_int, required=True, help="Number of grid columns.")
    sprite_parser.add_argument("--rows", type=positive_int, required=True, help="Number of grid rows.")
    sprite_parser.add_argument("--origin-x", type=nonnegative_int, default=0, help="Grid left edge in source pixels. Default: 0.")
    sprite_parser.add_argument("--origin-y", type=nonnegative_int, default=0, help="Grid top edge in source pixels. Default: 0.")
    sprite_parser.add_argument("--cell-width", type=positive_int, help="Crop width. Defaults to an exact calculation from the image width.")
    sprite_parser.add_argument("--cell-height", type=positive_int, help="Crop height. Defaults to an exact calculation from the image height.")
    sprite_parser.add_argument("--gap-x", type=nonnegative_int, default=0, help="Horizontal gap between cells. Default: 0.")
    sprite_parser.add_argument("--gap-y", type=nonnegative_int, default=0, help="Vertical gap between cells. Default: 0.")
    sprite_parser.add_argument("--margin-right", type=nonnegative_int, default=0, help="Ignored right-edge margin when deriving cell width. Default: 0.")
    sprite_parser.add_argument("--margin-bottom", type=nonnegative_int, default=0, help="Ignored bottom-edge margin when deriving cell height. Default: 0.")
    sprite_parser.add_argument("--labels", help="Comma-separated names in row-major order, one per cell.")
    sprite_parser.add_argument("--prefix", default="icon", help="Output filename prefix. Default: icon.")
    sprite_parser.add_argument("--output-dir", type=Path, help="Directory for cut icons and metadata. Default: <input>-sprites.")
    sprite_parser.add_argument("--format", type=parse_format, default="PNG", help="Format for individual cuts. Default: PNG.")
    sprite_parser.add_argument("--quality", type=positive_int, default=90, help="JPEG, WebP, and AVIF quality. Default: 90.")
    sprite_parser.add_argument("--background", type=parse_color, default=(255, 255, 255, 255), help="Background used when writing formats without alpha. Default: white.")
    sprite_parser.add_argument("--ico-sizes", default="16,32,48,64,128,256", help="Comma-separated square sizes for ICO cuts.")
    sprite_parser.add_argument("--trim", action="store_true", help="Trim transparent margins from each cut after extraction.")
    sprite_parser.add_argument("--padding", type=nonnegative_int, default=0, help="Padding applied with --trim. Default: 0.")
    sprite_parser.add_argument("--square", action="store_true", help="Create square output canvases with --trim.")
    sprite_parser.add_argument("--metadata", type=Path, help="Metadata JSON path. Default: <output-dir>/<prefix>.json.")
    sprite_parser.add_argument("--css", type=Path, help="Optional CSS file with exact background offsets.")
    sprite_parser.add_argument("--css-class", default="sprite", help="Base CSS class name. Default: sprite.")
    sprite_parser.add_argument("--image-url", help="Sprite-sheet URL used in generated CSS. Default: input filename.")
    sprite_parser.add_argument("--css-scale", type=float, default=1.0, help="CSS pixels per source pixel. Default: 1.")
    sprite_parser.add_argument("--preview", type=Path, help="Optional annotated source image showing each crop rectangle.")
    sprite_parser.add_argument("--overwrite", action="store_true", help="Replace existing outputs.")
    sprite_parser.set_defaults(handler=command_sprite_grid)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "quality") and not 1 <= args.quality <= 100:
        parser.error("--quality must be between 1 and 100")
    if hasattr(args, "opacity") and not 0 <= args.opacity <= 1:
        parser.error("--opacity must be between 0 and 1")
    if hasattr(args, "css_scale") and args.css_scale <= 0:
        parser.error("--css-scale must be positive")
    try:
        normalize_ico_sizes(args)
        args.handler(args)
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
