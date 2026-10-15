from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aladin_capture.capture import dry_run_plan, page_filename, run_capture
from aladin_capture.config import ConfigError, load_config, validate_config, CaptureConfig, Region
from aladin_capture.cli import main


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "config.example.yaml"


def test_example_config_loads():
    cfg = load_config(EXAMPLE)
    assert cfg.title == "example-book"
    assert cfg.pages == 10
    assert cfg.next_page == "key:right"
    assert cfg.region.width > 0


def test_validate_rejects_bad_next_page(tmp_path: Path):
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["capture"]["next_page"] = "teleport"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    with pytest.raises(ConfigError, match="next_page"):
        load_config(path)


def test_validate_rejects_tiny_region():
    cfg = CaptureConfig(
        title="t",
        pages=1,
        region=Region(0, 0, 10, 10),
        delay_ms=100,
        start_delay_sec=0,
        next_page="key:right",
        output_dir=Path("out"),
        save_images=True,
        save_pdf=False,
        zero_pad=4,
        min_region_px=50,
        personal_use_notice=False,
    )
    with pytest.raises(ConfigError, match="too small"):
        validate_config(cfg)


def test_dry_run_plan_shape():
    cfg = load_config(EXAMPLE)
    plan = dry_run_plan(cfg)
    assert plan["mode"] == "dry-run"
    assert len(plan["planned_files"]) == cfg.pages
    assert plan["planned_files"][0]["file"] == page_filename(cfg, 1)


def test_run_capture_with_injected_grab(tmp_path: Path):
    cfg = CaptureConfig(
        title="injected",
        pages=3,
        region=Region(0, 0, 200, 300),
        delay_ms=1,
        start_delay_sec=0,
        next_page="key:right",
        output_dir=tmp_path,
        save_images=True,
        save_pdf=False,
        zero_pad=3,
        min_region_px=50,
        personal_use_notice=False,
    )
    advances: list[str] = []
    # Minimal valid 1x1 PNG
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    book_dir = run_capture(
        cfg,
        grab=lambda _m: png,
        advance=lambda mode: advances.append(mode),
        sleep=lambda _s: None,
        log=lambda _m: None,
    )
    assert book_dir.is_dir()
    assert (book_dir / "page-001.png").is_file()
    assert (book_dir / "page-003.png").is_file()
    assert advances == ["key:right", "key:right"]
    manifest = json.loads((book_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["pages_requested"] == 3
    assert len(manifest["files"]) == 3


def test_cli_validate_and_dry_run(capsys):
    assert main(["validate-config", "-c", str(EXAMPLE)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["title"] == "example-book"

    assert main(["dry-run", "-c", str(EXAMPLE)]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["mode"] == "dry-run"
    assert plan["pages"] == 10
