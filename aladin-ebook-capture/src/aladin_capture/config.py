"""Load and validate YAML capture configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ALLOWED_NEXT_PAGE = frozenset({"key:right", "key:left", "key:pagedown", "click"})


@dataclass(frozen=True)
class Region:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def as_mss_monitor(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class CaptureConfig:
    title: str
    pages: int
    region: Region
    delay_ms: int
    start_delay_sec: float
    next_page: str
    output_dir: Path
    save_images: bool
    save_pdf: bool
    zero_pad: int
    min_region_px: int
    personal_use_notice: bool

    @property
    def book_dir(self) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_ ." else "_" for c in self.title).strip()
        return self.output_dir / (safe or "book")


class ConfigError(ValueError):
    """Invalid or incomplete configuration."""


def _require_mapping(data: Any, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ConfigError(f"{label} must be a mapping")
    return data


def load_config(path: Path | str) -> CaptureConfig:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    data = _require_mapping(raw, "root")
    book = _require_mapping(data.get("book"), "book")
    capture = _require_mapping(data.get("capture"), "capture")
    output = _require_mapping(data.get("output"), "output")
    safety = data.get("safety") or {}
    if safety is None:
        safety = {}
    if not isinstance(safety, dict):
        raise ConfigError("safety must be a mapping")

    region_raw = _require_mapping(capture.get("region"), "capture.region")
    try:
        region = Region(
            left=int(region_raw["left"]),
            top=int(region_raw["top"]),
            right=int(region_raw["right"]),
            bottom=int(region_raw["bottom"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"capture.region is incomplete or invalid: {exc}") from exc

    title = str(book.get("title", "")).strip()
    if not title:
        raise ConfigError("book.title is required")

    try:
        pages = int(book["pages"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError("book.pages must be a positive integer") from exc

    next_page = str(capture.get("next_page", "key:right")).strip().lower()
    delay_ms = int(capture.get("delay_ms", 400))
    start_delay_sec = float(capture.get("start_delay_sec", 3))
    out_dir = Path(str(output.get("dir", "./output")))
    save_images = bool(output.get("images", True))
    save_pdf = bool(output.get("pdf", True))
    zero_pad = int(output.get("zero_pad", 4))
    min_region_px = int(safety.get("min_region_px", 50))
    personal_use_notice = bool(safety.get("personal_use_notice", True))

    cfg = CaptureConfig(
        title=title,
        pages=pages,
        region=region,
        delay_ms=delay_ms,
        start_delay_sec=start_delay_sec,
        next_page=next_page,
        output_dir=out_dir,
        save_images=save_images,
        save_pdf=save_pdf,
        zero_pad=zero_pad,
        min_region_px=min_region_px,
        personal_use_notice=personal_use_notice,
    )
    validate_config(cfg)
    return cfg


def validate_config(cfg: CaptureConfig) -> list[str]:
    """Raise ConfigError on hard failures; return soft warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    if cfg.pages < 1:
        errors.append("book.pages must be >= 1")
    if cfg.delay_ms < 1:
        errors.append("capture.delay_ms must be >= 1")
    if cfg.start_delay_sec < 0:
        errors.append("capture.start_delay_sec must be >= 0")
    if cfg.next_page not in ALLOWED_NEXT_PAGE:
        errors.append(
            f"capture.next_page must be one of {sorted(ALLOWED_NEXT_PAGE)}, got {cfg.next_page!r}"
        )
    if cfg.region.width < cfg.min_region_px or cfg.region.height < cfg.min_region_px:
        errors.append(
            f"capture.region is too small ({cfg.region.width}x{cfg.region.height}); "
            f"need at least {cfg.min_region_px}px on each side"
        )
    if cfg.region.left < 0 or cfg.region.top < 0:
        warnings.append("capture.region has negative left/top (unusual for primary monitor)")
    if not cfg.save_images and not cfg.save_pdf:
        errors.append("output.images and output.pdf cannot both be false")
    if cfg.zero_pad < 1 or cfg.zero_pad > 8:
        errors.append("output.zero_pad must be between 1 and 8")

    if errors:
        raise ConfigError("; ".join(errors))
    return warnings
