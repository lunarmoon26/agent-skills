from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "photocraft_tool.py"
SPEC = importlib.util.spec_from_file_location("photocraft_tool", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class BridgeTests(unittest.TestCase):
    def test_rejects_invalid_requests_before_launch(self):
        invalid = [None, {}, {"command": "serve", "arguments": []},
                   {"command": [], "arguments": []},
                   {"command": "info", "arguments": [1]},
                   {"command": "info", "arguments": [], "extra": True}]
        with patch.object(tool.subprocess, "run") as run:
            for request in invalid:
                with self.subTest(request=request), self.assertRaises(ValueError):
                    tool.execute(request)
            run.assert_not_called()

    def test_missing_executable(self):
        with patch.object(tool.shutil, "which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "not on PATH"):
                tool.execute({"command": "info", "arguments": ["input.psd"]})

    def test_preserves_tokens_and_parses_pretty_json_and_warnings(self):
        arguments = ["file with spaces.psd", "--cmd", "test", "--params", '{"text":"$(no shell)"}']
        result = subprocess.CompletedProcess([], 0, '[\n  {"id": "test"}\n]\n', "warning: font missing\n")
        with patch.object(tool.shutil, "which", return_value="/bin/photocraft-cli"), \
                patch.object(tool.subprocess, "run", return_value=result) as run:
            output = tool.execute({"command": "run", "arguments": arguments})
        self.assertEqual(run.call_args.args[0], ["/bin/photocraft-cli", "run", *arguments])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["timeout"], 590)
        self.assertEqual(output["records"], [[{"id": "test"}]])
        self.assertEqual(output["warnings"], ["warning: font missing"])

    def test_json_lines_and_empty_conversion_output(self):
        for stdout, records in [('{}\n{"result":1}\n', [{}, {"result": 1}]), ("", [])]:
            with self.subTest(stdout=stdout), \
                    patch.object(tool.shutil, "which", return_value="photocraft-cli"), \
                    patch.object(tool.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout, "")):
                self.assertEqual(tool.execute({"command": "convert", "arguments": []})["records"], records)

    def test_cli_failure_is_not_success(self):
        with patch.object(tool.shutil, "which", return_value="photocraft-cli"), \
                patch.object(tool.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "bad command")):
            with self.assertRaisesRegex(ValueError, "exited 1: bad command"):
                tool.execute({"command": "run", "arguments": []})

    def test_timeout_propagates_to_entrypoint(self):
        with patch.object(tool.shutil, "which", return_value="photocraft-cli"), \
                patch.object(tool.subprocess, "run", side_effect=subprocess.TimeoutExpired("photocraft-cli", 590)):
            with self.assertRaises(subprocess.TimeoutExpired):
                tool.execute({"command": "run", "arguments": []})

    def test_json_entrypoint_rejects_malformed_input(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input="{", text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("photocraft:", result.stderr)


@unittest.skipUnless(shutil.which("photocraft-cli"), "PhotoCraft CLI not installed")
class LiveCliTests(unittest.TestCase):
    def call(self, command, arguments):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], input=json.dumps({"command": command, "arguments": arguments}),
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_layered_master_preview_and_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            master = root / "input.pcraft"
            edited = root / "edited.pcraft"
            preview = root / "preview.png"
            self.call("run", ["--new", '{"width":16,"height":12,"background":"white"}', "--out", str(master)])
            commands = self.call("commands", ["--json", "--filter", "layer.newAdjustmentLayer.curves"])
            self.assertTrue(commands["records"][0])
            params = '{"points":[[0,0],[64,48],[192,212],[255,255]]}'
            self.call("run", [str(master), "--cmd", "layer.newAdjustmentLayer.curves", "--params", params, "--out", str(edited)])
            self.call("convert", [str(edited), str(preview)])
            info = self.call("info", [str(edited), "--compact"])["records"][0]
            self.assertEqual((info["width"], info["height"]), (16, 12))
            self.assertEqual(len(info["layers"]), 2)
            self.assertIn("Curves", info["layers"][0]["adjustment"])
            psd = root / "edited.psd"
            self.call("convert", [str(edited), str(psd)])
            psd_info = self.call("info", [str(psd), "--compact"])["records"][0]
            self.assertEqual(len(psd_info["layers"]), 2)
            self.assertIn("Curves", psd_info["layers"][0]["adjustment"])
            self.assertTrue(preview.is_file())
            raw = root / "raw"
            raw.mkdir()
            shutil.copyfile(master, raw / master.name)
            actions = root / "grade.json"
            actions.write_text(json.dumps([{"command": "layer.newAdjustmentLayer.curves", "params": json.loads(params)}]))
            graded = root / "graded"
            self.call("batch", ["--actions", str(actions), "--in", str(raw), "--out", str(graded), "--format", "png"])
            self.assertTrue((graded / "input.png").is_file())


if __name__ == "__main__":
    unittest.main()
