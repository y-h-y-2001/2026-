from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aladin_capture.capture import dry_run_plan, page_filename, run_capture
from aladin_capture.config import ConfigError, load_config, validate_config, CaptureConfig, Region
from aladin_capture.cli import main
from aladin_capture.macos import doctor_report, region_to_mss


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "config.example.yaml"


def test_example_config_loads():
    cfg = load_config(EXAMPLE)
    assert cfg.title == "example-book"
    assert cfg.pages == 10
    assert cfg.next_page == "key:right"
    assert cfg.coordinate_space == "logical"
    assert cfg.retina_scale is None
    assert cfg.save_images is True
    assert cfg.save_pdf is True
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


def test_region_to_mss_logical_retina():
    region = Region(10, 20, 110, 220)
    mon = region_to_mss(region, coordinate_space="logical", scale=2.0)
    assert mon == {"left": 20, "top": 40, "width": 200, "height": 400}


def test_region_to_mss_physical_unchanged():
    region = Region(10, 20, 110, 220)
    mon = region_to_mss(region, coordinate_space="physical", scale=2.0)
    assert mon == {"left": 10, "top": 20, "width": 100, "height": 200}


def test_dry_run_plan_includes_macos_scale():
    cfg = load_config(EXAMPLE)
    plan = dry_run_plan(cfg)
    assert plan["mode"] == "dry-run"
    assert plan["target_os"] == "macOS"
    assert "mss_region_physical" in plan
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
        coordinate_space="logical",
        retina_scale=2.0,
    )
    advances: list[str] = []
    grabbed: list[dict] = []
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def grab(mon: dict) -> bytes:
        grabbed.append(mon)
        return png

    book_dir = run_capture(
        cfg,
        grab=grab,
        advance=lambda mode: advances.append(mode),
        sleep=lambda _s: None,
        log=lambda _m: None,
    )
    assert book_dir.is_dir()
    assert (book_dir / "page-001.png").is_file()
    assert advances == ["key:right", "key:right"]
    # logical 200x300 at scale 2 → physical 400x600
    assert grabbed[0]["width"] == 400
    assert grabbed[0]["height"] == 600
    manifest = json.loads((book_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["target_os"] == "macOS"
    assert manifest["retina_scale"]["scale"] == 2.0


def test_cli_validate_dry_run_doctor(capsys):
    assert main(["validate-config", "-c", str(EXAMPLE)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["target_os"] == "macOS"
    assert data["output_pdf"] is True

    assert main(["dry-run", "-c", str(EXAMPLE)]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["mode"] == "dry-run"
    assert plan["pages"] == 10

    assert main(["doctor"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["target_os"] == "macOS"
    assert "aladin_viewer" in report


def test_doctor_report_shape():
    report = doctor_report()
    assert report["target_os"] == "macOS"
    assert "display_scale" in report
    assert "permissions" in report
