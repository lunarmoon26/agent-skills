from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).parents[1] / "scripts" / "compare.py"
SPEC = importlib.util.spec_from_file_location("vector_compare", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
compare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compare)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.reference = self.root / "reference.png"
        self.rendered = self.root / "rendered.png"
        Image.new("RGBA", (4, 3), (10, 20, 30, 255)).save(self.reference)
        Image.new("RGBA", (4, 3), (10, 20, 30, 255)).save(self.rendered)

    def test_identical_images_and_output_dimensions(self):
        output = self.root / "checks"
        report = compare.compare(self.reference, self.rendered, output, "#ffffff")
        self.assertEqual(report["rgb_mae"], 0)
        self.assertEqual(report["alpha_mae"], 0)
        self.assertEqual(json.loads((output / "report.json").read_text()), report)
        with Image.open(output / "side-by-side.png") as image:
            self.assertEqual(image.size, (8, 3))
        with Image.open(output / "difference.png") as image:
            self.assertIsNone(image.getbbox())

    def test_known_difference_and_overlay(self):
        Image.new("RGBA", (4, 3), (20, 40, 60, 255)).save(self.rendered)
        output = self.root / "checks"
        report = compare.compare(self.reference, self.rendered, output, "#ffffff")
        self.assertEqual(report["rgb_channel_mae"], [10, 20, 30])
        self.assertEqual(report["rgb_mae"], 20)
        with Image.open(output / "overlay.png") as image:
            self.assertEqual(image.getpixel((0, 0)), (15, 30, 45))

    def test_alpha_is_reported_separately_and_background_is_shared(self):
        Image.new("RGBA", (4, 3), (255, 0, 0, 0)).save(self.reference)
        Image.new("RGBA", (4, 3), (255, 255, 255, 255)).save(self.rendered)
        report = compare.compare(self.reference, self.rendered, self.root / "white", "#ffffff")
        self.assertEqual(report["rgb_mae"], 0)
        self.assertEqual(report["alpha_mae"], 255)
        black = compare.compare(self.reference, self.rendered, self.root / "black", "#000000")
        self.assertEqual(black["rgb_mae"], 255)

    def test_dimension_and_background_errors_write_nothing(self):
        output = self.root / "checks"
        with self.assertRaisesRegex(ValueError, "#RRGGBB"):
            compare.compare(self.reference, self.rendered, output, "white")
        Image.new("RGBA", (5, 3)).save(self.rendered)
        with self.assertRaisesRegex(ValueError, "dimensions differ"):
            compare.compare(self.reference, self.rendered, output, "#ffffff")
        self.assertFalse(output.exists())

    def test_existing_outputs_refused_and_explicit_overwrite_allowed(self):
        output = self.root / "checks"
        compare.compare(self.reference, self.rendered, output, "#ffffff")
        with self.assertRaises(FileExistsError):
            compare.compare(self.reference, self.rendered, output, "#ffffff")
        compare.compare(self.reference, self.rendered, output, "#ffffff", overwrite=True)

    def test_inputs_never_replaced_even_with_overwrite(self):
        protected = self.root / "overlay.png"
        self.reference.rename(protected)
        original = protected.read_bytes()
        with self.assertRaisesRegex(ValueError, "replace an input"):
            compare.compare(protected, self.rendered, self.root, "#ffffff", overwrite=True)
        self.assertEqual(protected.read_bytes(), original)
        self.assertFalse((self.root / "side-by-side.png").exists())

    def test_animation_rejected(self):
        animated = self.root / "reference.gif"
        Image.new("RGB", (4, 3), "red").save(animated, save_all=True, append_images=[Image.new("RGB", (4, 3), "blue")])
        with self.assertRaisesRegex(ValueError, "multi-frame"):
            compare.compare(animated, self.rendered, self.root / "checks", "#ffffff")

    def test_dangling_and_aliasing_output_symlinks_rejected(self):
        for target in ("missing.png", "side-by-side.png"):
            with self.subTest(target=target):
                output = self.root / target.removesuffix(".png")
                output.mkdir()
                try:
                    (output / "overlay.png").symlink_to(target)
                except OSError as error:
                    self.skipTest(f"symlinks unavailable: {error}")
                with self.assertRaisesRegex(ValueError, "symlink output"):
                    compare.compare(self.reference, self.rendered, output, "#ffffff", overwrite=True)
                self.assertFalse((output / "side-by-side.png").exists())

    def test_cli_json_and_nonzero_failure(self):
        arguments = [sys.executable, str(SCRIPT), str(self.reference), str(self.rendered), "--output-dir", str(self.root / "checks")]
        result = subprocess.run(arguments, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["rgb_mae"], 0)
        repeated = subprocess.run(arguments, capture_output=True, text=True)
        self.assertEqual(repeated.returncode, 2)
        self.assertEqual(repeated.stdout, "")


if __name__ == "__main__":
    unittest.main()
