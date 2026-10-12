from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "photo.py"
TOOL_SCRIPT = ROOT / "scripts" / "tool.py"
SPEC = importlib.util.spec_from_file_location("photo", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
photo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(photo)


def call(*arguments):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
                          capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize("command", ["inspect", "key-color", "flood-fill", "mask", "trim"])
def test_removed_commands_rejected_by_cli_and_bridge(command):
    result = call(command)
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    result = subprocess.run([sys.executable, str(TOOL_SCRIPT)],
                            input=json.dumps({"command": command, "arguments": []}),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "unsupported photo command" in result.stderr


def test_resize_keeps_alpha_and_overwrite_guard(tmp_path):
    source = tmp_path / "sample.png"
    destination = tmp_path / "sample-resized.png"
    Image.new("RGBA", (3, 2), (17, 34, 51, 68)).save(source)
    original = source.read_bytes()
    result = call("resize", source, "--width", 6, "--height", 4)
    assert result.returncode == 0, result.stderr
    with Image.open(destination) as output:
        assert output.size == (6, 4)
        assert output.convert("RGBA").getpixel((3, 2))[3] == 68
    result = call("resize", source, "--width", 6, "--height", 4)
    assert result.returncode == 2
    assert "output exists; pass --overwrite" in result.stderr
    assert source.read_bytes() == original


def test_multisize_ico_export(tmp_path):
    source, destination = tmp_path / "sample.png", tmp_path / "favicon.ico"
    Image.new("RGBA", (64, 64), (10, 20, 30, 255)).save(source)
    result = call("resize", source, "--width", 64, "--height", 64,
                  "--output", destination, "--ico-sizes", "16,32,64")
    assert result.returncode == 0, result.stderr
    with Image.open(destination) as output:
        assert output.ico.sizes() == {(16, 16), (32, 32), (64, 64)}


def test_luminance_alpha_normalizes_black_backed_pixels():
    image = Image.new("RGBA", (3, 1))
    image.putdata([(0, 0, 0, 255), (128, 128, 128, 255), (255, 255, 255, 255)])
    result = photo.luminance_alpha(image, 0, 255, 1, 0, "replace", 0)
    assert list(result.get_flattened_data()) == [
        (0, 0, 0, 0), (255, 255, 255, 128), (255, 255, 255, 255)]


def test_sprite_grid_keeps_internal_trim_padding_and_metadata(tmp_path):
    source, output_dir = tmp_path / "sheet.png", tmp_path / "cuts"
    image = Image.new("RGBA", (8, 4))
    image.putpixel((1, 1), (255, 0, 0, 255))
    image.putpixel((5, 2), (0, 255, 0, 255))
    image.save(source)
    css = tmp_path / "sprites.css"
    result = call("sprite-grid", source, "--columns", 2, "--rows", 1,
                  "--output-dir", output_dir, "--prefix", "icon", "--trim",
                  "--padding", 1, "--square", "--css", css)
    assert result.returncode == 0, result.stderr
    metadata = json.loads((output_dir / "icon.json").read_text())
    assert metadata["cells"][0]["sourceRect"] == [0, 0, 4, 4]
    assert metadata["cells"][1]["sourceRect"] == [4, 0, 4, 4]
    assert metadata["cells"][1]["backgroundPosition"] == [-4, 0]
    for cell in metadata["cells"]:
        with Image.open(output_dir / cell["output"]) as output:
            assert output.size == (3, 3)
            assert output.convert("RGBA").getpixel((1, 1))[3] == 255
    positions = re.findall(r"background-position: ([-\d.]+)px ([-\d.]+)px", css.read_text())
    assert [(float(x), float(y)) for x, y in positions] == [(0, 0), (-4, 0)]


def test_json_bridge_and_manifest_commands_agree(tmp_path):
    source, destination = tmp_path / "source.png", tmp_path / "out.png"
    Image.new("RGBA", (3, 2), (1, 2, 3, 4)).save(source)
    result = subprocess.run([sys.executable, str(TOOL_SCRIPT)],
                            input=json.dumps({"command": "resize", "arguments": [
                                str(source), "--width", "6", "--height", "4", "--output", str(destination)]}),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True and payload["command"] == "resize"
    assert payload["messages"]
    with Image.open(destination) as output:
        assert output.size == (6, 4)
    manifest = json.loads((ROOT / "skill-runtime.json").read_text())
    expected = {"resize", "key-luminance", "sprite-grid"}
    spec = importlib.util.spec_from_file_location("photo_tool", TOOL_SCRIPT)
    bridge = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOL_SCRIPT.parent))
    try:
        spec.loader.exec_module(bridge)
    finally:
        sys.path.pop(0)
    assert bridge.COMMANDS == expected
    assert set(manifest["tools"][0]["inputSchema"]["properties"]["command"]["enum"]) == expected
