from __future__ import annotations

# pyright: reportMissingImports=false
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).parents[1] / "scripts" / "photo.py"
TOOL_SCRIPT = Path(__file__).parents[1] / "scripts" / "tool.py"
SPEC = importlib.util.spec_from_file_location("photo", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not import {SCRIPT}")
photo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(photo)


class FloodFillColorTests(unittest.TestCase):
    def test_preserves_enclosed_pixels_with_the_same_color(self) -> None:
        image = Image.new("RGBA", (7, 7), (0, 0, 0, 255))
        pixels = image.load()
        for coordinate in range(2, 5):
            pixels[coordinate, 2] = (255, 255, 255, 255)
            pixels[coordinate, 4] = (255, 255, 255, 255)
            pixels[2, coordinate] = (255, 255, 255, 255)
            pixels[4, coordinate] = (255, 255, 255, 255)

        output, count = photo.flood_fill_color(
            image,
            seed_x=0,
            seed_y=0,
            color=(0, 0, 0, 0),
            tolerance=0,
            alpha_mode="match",
            connectivity=8,
        )

        self.assertEqual(count, 40)
        self.assertEqual(output.getpixel((0, 0)), (0, 0, 0, 0))
        self.assertEqual(output.getpixel((3, 3)), (0, 0, 0, 255))
        self.assertEqual(output.getpixel((3, 2)), (255, 255, 255, 255))

    def test_tolerance_is_per_channel_and_fixed_to_the_seed(self) -> None:
        image = Image.new("RGBA", (4, 1))
        image.putdata(
            [
                (100, 100, 100, 255),
                (105, 94, 110, 255),
                (110, 110, 90, 255),
                (115, 100, 100, 255),
            ]
        )

        output, count = photo.flood_fill_color(
            image,
            seed_x=0,
            seed_y=0,
            color=(255, 0, 0, 255),
            tolerance=10,
            alpha_mode="match",
            connectivity=8,
        )

        self.assertEqual(count, 3)
        self.assertEqual(list(output.get_flattened_data())[:3], [(255, 0, 0, 255)] * 3)
        self.assertEqual(output.getpixel((3, 0)), (115, 100, 100, 255))

    def test_alpha_can_be_matched_or_ignored(self) -> None:
        image = Image.new("RGBA", (2, 1))
        image.putdata([(20, 30, 40, 0), (20, 30, 40, 255)])

        matched, matched_count = photo.flood_fill_color(
            image,
            seed_x=0,
            seed_y=0,
            color=(1, 2, 3, 4),
            tolerance=0,
            alpha_mode="match",
            connectivity=8,
        )
        ignored, ignored_count = photo.flood_fill_color(
            image,
            seed_x=0,
            seed_y=0,
            color=(1, 2, 3, 4),
            tolerance=0,
            alpha_mode="ignore",
            connectivity=8,
        )

        self.assertEqual(matched_count, 1)
        self.assertEqual(matched.getpixel((1, 0)), (20, 30, 40, 255))
        self.assertEqual(ignored_count, 2)
        self.assertEqual(ignored.getpixel((1, 0)), (1, 2, 3, 4))

    def test_connectivity_controls_diagonal_selection(self) -> None:
        image = Image.new("RGBA", (2, 2), (255, 255, 255, 255))
        image.putpixel((0, 0), (0, 0, 0, 255))
        image.putpixel((1, 1), (0, 0, 0, 255))

        _, four_way_count = photo.flood_fill_color(
            image, 0, 0, (255, 0, 0, 255), 0, "match", 4
        )
        _, eight_way_count = photo.flood_fill_color(
            image, 0, 0, (255, 0, 0, 255), 0, "match", 8
        )

        self.assertEqual(four_way_count, 1)
        self.assertEqual(eight_way_count, 2)

    def test_rejects_seed_outside_image(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside the 2x2 image"):
            photo.flood_fill_color(
                Image.new("RGBA", (2, 2)), 2, 0, (0, 0, 0, 0), 0, "match", 8
            )

    def test_cli_writes_default_output_and_refuses_implicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "sample.png"
            destination = directory / "sample-filled.png"
            image = Image.new("RGBA", (3, 1))
            image.putdata([(0, 0, 0, 255), (0, 0, 0, 255), (255, 255, 255, 255)])
            image.save(source)
            command = [
                sys.executable,
                str(SCRIPT),
                "flood-fill",
                str(source),
                "--x",
                "0",
                "--y",
                "0",
                "--color",
                "#11223344",
            ]

            first_run = subprocess.run(command, capture_output=True, text=True, check=False)

            self.assertEqual(first_run.returncode, 0, first_run.stderr)
            self.assertTrue(destination.exists())
            with Image.open(destination) as output:
                self.assertEqual(output.convert("RGBA").getpixel((0, 0)), (17, 34, 51, 68))
                self.assertEqual(output.convert("RGBA").getpixel((1, 0)), (17, 34, 51, 68))
                self.assertEqual(output.convert("RGBA").getpixel((2, 0)), (255, 255, 255, 255))

            second_run = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(second_run.returncode, 2)
            self.assertIn("output exists; pass --overwrite", second_run.stderr)

    def test_json_tool_bridge_returns_structured_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "sample.png"
            Image.new("RGBA", (3, 2), (1, 2, 3, 4)).save(source)

            result = subprocess.run(
                [sys.executable, str(TOOL_SCRIPT)],
                input=json.dumps({"command": "inspect", "arguments": [str(source)]}),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["command"], "inspect")
            self.assertEqual(payload["records"][0]["size"], [3, 2])
            self.assertEqual(payload["records"][0]["format"], "PNG")


if __name__ == "__main__":
    unittest.main()
