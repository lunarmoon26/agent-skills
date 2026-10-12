import importlib.util
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

spec = importlib.util.spec_from_file_location(
    "trace_prepare", Path(__file__).parents[1] / "scripts" / "trace_prepare.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_noise_reduction_preserves_strong_edge(tmp_path):
    rng = np.random.default_rng(42)
    pixels = np.zeros((40, 60, 3), dtype=np.int16)
    pixels[:, :30] = 40
    pixels[:, 30:] = 210
    pixels += rng.integers(-5, 6, pixels.shape)
    pixels = pixels.astype(np.uint8)
    source, output = tmp_path / "source.png", tmp_path / "filtered.png"
    Image.fromarray(pixels).save(source)
    original = source.read_bytes()
    report = module.prepare(source, output)
    result = np.array(Image.open(output))
    assert report["width"] == 60 and report["height"] == 40
    assert result[:, 5:25].std() < pixels[:, 5:25].std()
    assert result[:, 30].mean() - result[:, 29].mean() > 150
    assert source.read_bytes() == original


def test_refuses_unsafe_outputs_and_parameters(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (10, 10), "red").save(source)
    for output, kwargs in [(source, {}), (tmp_path / "out.jpg", {}),
                           (tmp_path / "out.png", {"sigma_color": float("nan")}),
                           (tmp_path / "out.png", {"diameter": 0})]:
        with pytest.raises(ValueError):
            module.prepare(source, output, **kwargs)
    output = tmp_path / "exists.png"
    output.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        module.prepare(source, output)
    assert output.read_bytes() == b"keep"


def test_refuses_dangling_symlink(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (10, 10), "red").save(source)
    link = tmp_path / "link.png"
    try:
        link.symlink_to(tmp_path / "missing.png")
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this platform")
    with pytest.raises(FileExistsError):
        module.prepare(source, link)


def test_refuses_alpha_animation_and_icc(tmp_path):
    source, output = tmp_path / "source.png", tmp_path / "out.png"
    Image.new("RGBA", (10, 10), (255, 0, 0, 128)).save(source)
    with pytest.raises(ValueError, match="alpha-aware"):
        module.prepare(source, output)
    Image.new("RGB", (10, 10)).save(source, icc_profile=b"tagged")
    with pytest.raises(ValueError, match="ICC"):
        module.prepare(source, output)
    source = tmp_path / "animated.gif"
    Image.new("RGB", (10, 10), "red").save(
        source, save_all=True, append_images=[Image.new("RGB", (10, 10), "blue")])
    with pytest.raises(ValueError, match="multi-frame"):
        module.prepare(source, output)
    assert not output.exists()
