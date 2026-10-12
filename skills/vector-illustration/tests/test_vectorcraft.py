from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "tool.py"
SPEC = importlib.util.spec_from_file_location("vectorcraft_tool", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class BridgeTests(unittest.TestCase):
    def test_invalid_requests_never_launch(self):
        invalid = [None, {}, {"command": "mcp", "arguments": []},
                   {"command": [], "arguments": []}, {"command": "run", "arguments": [1]},
                   {"command": "run", "arguments": [], "extra": True}]
        with patch.object(tool.subprocess, "run") as run:
            for request in invalid:
                with self.subTest(request=request), self.assertRaises(ValueError):
                    tool.execute(request)
            run.assert_not_called()

    def test_missing_cli(self):
        with patch.object(tool.shutil, "which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "not on PATH"):
                tool.execute({"command": "commands", "arguments": []})

    def test_tokens_json_and_warnings(self):
        args = ["--in", "source with spaces.svg", "--cmd", "object.setProps", "--params", '{"name":"$(no shell)"}']
        result = subprocess.CompletedProcess([], 0, '[\n {"id":"shape.ellipse"}\n]\n', "warning: fallback font\n")
        with patch.object(tool.shutil, "which", return_value="/bin/vectorcraft-cli"), \
                patch.object(tool.subprocess, "run", return_value=result) as run:
            output = tool.execute({"command": "run", "arguments": args})
        self.assertEqual(run.call_args.args[0], ["/bin/vectorcraft-cli", "run", *args])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["timeout"], 590)
        self.assertEqual(output["records"], [[{"id": "shape.ellipse"}]])
        self.assertEqual(output["warnings"], ["warning: fallback font"])

    def test_json_lines_and_empty_stdout(self):
        for stdout, records in [('{}\n{"result":1}\n', [{}, {"result": 1}]), ("", [])]:
            with self.subTest(stdout=stdout), \
                    patch.object(tool.shutil, "which", return_value="vectorcraft-cli"), \
                    patch.object(tool.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout, "")):
                self.assertEqual(tool.execute({"command": "convert", "arguments": []})["records"], records)

    def test_failure_and_timeout_do_not_return_success(self):
        with patch.object(tool.shutil, "which", return_value="vectorcraft-cli"), \
                patch.object(tool.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "bad command")):
            with self.assertRaisesRegex(ValueError, "exited 1: bad command"):
                tool.execute({"command": "run", "arguments": []})
        with patch.object(tool.shutil, "which", return_value="vectorcraft-cli"), \
                patch.object(tool.subprocess, "run", side_effect=subprocess.TimeoutExpired("vectorcraft-cli", 590)):
            with self.assertRaises(subprocess.TimeoutExpired):
                tool.execute({"command": "run", "arguments": []})

    def test_malformed_json_entrypoint(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input="{", capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("vectorcraft:", result.stderr)


@unittest.skipUnless(shutil.which("vectorcraft-cli"), "VectorCraft CLI not installed")
class LiveCliTests(unittest.TestCase):
    def call(self, command, arguments):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], input=json.dumps({"command": command, "arguments": arguments}),
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_create_native_svg_preview_and_recolor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            master, svg, png = (root / name for name in ["badge.vectorcraft", "badge.svg", "badge.png"])
            result = self.call("run", [
                "--cmd", "file.new", "--params", '{"title":"Badge","width":64,"height":64,"units":"Pixels"}',
                "--cmd", "shape.ellipse", "--params", '{"x":8,"y":8,"width":48,"height":48}',
                "--cmd", "paint.setFill", "--params", '{"color":"#2563eb","ids":["$1.id"]}',
                "--export", str(master), "--export", str(svg), "--export", str(png), "--scale", "4",
            ])
            self.assertEqual(len(result["records"]), 6)
            self.assertTrue(master.is_file())
            self.assertEqual(ET.parse(svg).getroot().tag, "{http://www.w3.org/2000/svg}svg")
            with Image.open(png) as image:
                self.assertEqual(image.size, (256, 256))
                self.assertEqual(image.convert("RGBA").getpixel((128, 128)), (37, 99, 235, 255))
                self.assertEqual(image.convert("RGBA").getpixel((0, 0))[3], 0)
            info = self.call("info", [str(master)])["records"][0]
            self.assertEqual(info["artboards"][0]["rect"][2:], [64, 64])
            tree = self.call("run", ["--in", str(master), "--cmd", "document.inspect", "--params", '{"depth":2,"childLimit":20}'])
            self.assertEqual(tree["records"][-1]["command"], "document.inspect")
            recolored = root / "recolored.svg"
            self.call("run", ["--in", str(svg), "--cmd", "select.all", "--cmd", "paint.setFill",
                              "--params", '{"color":"#ff3b30"}', "--export", str(recolored)])
            preview = root / "recolored.png"
            self.call("convert", [str(recolored), str(preview), "--scale", "4"])
            with Image.open(preview) as image:
                self.assertEqual(image.convert("RGBA").getpixel((128, 128)), (255, 59, 48, 255))

    def test_svg_first_import_discovery_and_render(self):
        commands = self.call("commands", [])["records"][0]
        self.assertIn("path.create", {command["id"] for command in commands})
        fixture = ROOT / "tests" / "fixtures" / "mountains.svg"
        info = self.call("info", [str(fixture)])["records"][0]
        self.assertEqual(info["artboards"][0]["rect"][2:], [24, 24])
        with tempfile.TemporaryDirectory() as directory:
            png = Path(directory) / "mountains.png"
            self.call("convert", [str(fixture), str(png), "--scale", "4"])
            with Image.open(png) as image:
                self.assertEqual(image.size, (96, 96))
                self.assertIsNotNone(image.convert("RGBA").getchannel("A").getbbox())

    def test_live_illustration_mechanisms_survive_native_reopen(self):
        cases = [
            ("Blend", [
                ("shape.rectangle", {"x":10,"y":10,"width":12,"height":12}),
                ("paint.setFill", {"color":"#ff3b30","ids":["$1.id"]}),
                ("shape.rectangle", {"x":80,"y":80,"width":20,"height":20}),
                ("paint.setFill", {"color":"#2563eb","ids":["$3.id"]}),
                ("object.blend.make", {"ids":["$1.id","$3.id"],"steps":8}),
            ]),
            ("Radial Repeat", [
                ("shape.ellipse", {"x":50,"y":50,"width":10,"height":20}),
                ("object.repeat.radial", {"ids":["$1.id"],"instances":8,"radius":30}),
            ]),
            ("Envelope", [
                ("shape.rectangle", {"x":20,"y":20,"width":80,"height":60}),
                ("object.envelope.makeWithWarp", {"ids":["$1.id"],"style":"flag","bend":45}),
            ]),
            ("Mesh", [
                ("shape.rectangle", {"x":20,"y":20,"width":80,"height":60}),
                ("object.mesh.create", {"ids":["$1.id"],"rows":4,"cols":4,"appearance":"center"}),
            ]),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for kind, steps in cases:
                with self.subTest(kind=kind):
                    master = Path(directory) / f"{kind}.vectorcraft"
                    png = Path(directory) / f"{kind}.png"
                    arguments = ["--cmd", "file.new", "--params", '{"width":128,"height":128,"units":"Pixels"}']
                    for command, params in steps:
                        arguments.extend(["--cmd", command, "--params", json.dumps(params)])
                    self.call("run", [*arguments, "--export", str(master)])
                    info = self.call("info", [str(master)])["records"][0]
                    self.assertGreaterEqual(info["kinds"].get(kind, 0), 1)
                    self.call("convert", [str(master), str(png)])
                    with Image.open(png) as image:
                        self.assertEqual(image.size, (128, 128))
                        self.assertIsNotNone(image.convert("RGBA").getchannel("A").getbbox())

    def test_perspective_plane_attachment_survives_native_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            master = Path(directory) / "perspective.vectorcraft"
            created = self.call("run", [
                "--cmd", "file.new", "--params", '{"width":1600,"height":1000}',
                "--cmd", "perspective.grid.preset", "--params", '{"kind":2}',
                "--cmd", "shape.rectangle", "--params", '{"x":330,"y":500,"width":60,"height":60}',
                "--cmd", "perspective.attach", "--params", '{"ids":["$2.id"],"plane":"right"}',
                "--export", str(master),
            ])
            object_id = created["records"][2]["result"]["id"]
            result = self.call("run", ["--in", str(master), "--cmd", "document.node", "--params", json.dumps({"id": object_id})])
            self.assertEqual(result["records"][-1]["result"]["perspective"]["plane"], "right")


if __name__ == "__main__":
    unittest.main()
