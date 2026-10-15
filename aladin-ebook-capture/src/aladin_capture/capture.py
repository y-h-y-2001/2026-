"""Region screenshot + page-advance loop.

Adapted from p0tat0-113/ebookAutoCapture (Tkinter GUI Capture class).
Retargeted for macOS + official 알라딘 eBook desktop viewer.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import CaptureConfig
from .macos import is_macos, region_to_mss, resolve_scale


PERSONAL_USE = (
    "Personal use only: capture pages from ebooks you purchased, "
    "via the official viewer. Do not redistribute captures or bypass DRM."
)


def _advance_page(mode: str) -> None:
    import pyautogui

    if mode == "key:right":
        pyautogui.press("right")
    elif mode == "key:left":
        pyautogui.press("left")
    elif mode == "key:pagedown":
        pyautogui.press("pagedown")
    elif mode == "key:space":
        pyautogui.press("space")
    elif mode == "click":
        pyautogui.click()
    else:
        raise ValueError(f"Unknown next_page mode: {mode}")


def page_filename(cfg: CaptureConfig, page: int) -> str:
    return f"page-{page:0{cfg.zero_pad}d}.png"


def dry_run_plan(cfg: CaptureConfig) -> dict:
    """Describe what capture would do without touching the screen."""
    scale_info = resolve_scale(cfg.retina_scale)
    mss_region = region_to_mss(
        cfg.region,
        coordinate_space=cfg.coordinate_space,
        scale=scale_info.scale,
    )
    pages = [
        {
            "page": i,
            "file": page_filename(cfg, i),
            "next_page_after": cfg.next_page if i < cfg.pages else None,
        }
        for i in range(1, cfg.pages + 1)
    ]
    return {
        "mode": "dry-run",
        "target_os": "macOS",
        "host_is_macos": is_macos(),
        "viewer": "알라딘 eBook (Mac App Store desktop app)",
        "book_title": cfg.title,
        "pages": cfg.pages,
        "region_config": asdict(cfg.region),
        "coordinate_space": cfg.coordinate_space,
        "retina_scale": scale_info.to_dict(),
        "mss_region_physical": mss_region,
        "delay_ms": cfg.delay_ms,
        "start_delay_sec": cfg.start_delay_sec,
        "next_page": cfg.next_page,
        "book_dir": str(cfg.book_dir.resolve()),
        "save_images": cfg.save_images,
        "save_pdf": cfg.save_pdf,
        "planned_files": pages,
        "notice": PERSONAL_USE,
        "mac_blocker_if_remote": (
            None
            if is_macos()
            else "Run capture on the user's Mac; this host cannot drive the Aladin window."
        ),
    }


def run_capture(
    cfg: CaptureConfig,
    *,
    dry_run: bool = False,
    grab: Callable[[dict], bytes] | None = None,
    advance: Callable[[str], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] | None = None,
) -> Path:
    """Capture pages into cfg.book_dir. Returns the book directory path.

    Inject grab/advance/sleep for tests. On a real run, grab uses mss (physical
    pixels) and advance uses pyautogui with the Aladin Mac viewer focused.
    """
    log = log or (lambda msg: print(msg, file=sys.stderr))

    if cfg.personal_use_notice:
        log(PERSONAL_USE)

    if dry_run:
        plan = dry_run_plan(cfg)
        log(json.dumps(plan, indent=2, ensure_ascii=False))
        return cfg.book_dir

    if grab is None and not is_macos():
        raise RuntimeError(
            "Real capture targets macOS with 알라딘 eBook open. "
            "This host is not macOS. Use dry-run / validate-config here, "
            "or run capture on the user's Mac."
        )

    book_dir = cfg.book_dir
    book_dir.mkdir(parents=True, exist_ok=True)

    scale_info = resolve_scale(cfg.retina_scale)
    mss_region = region_to_mss(
        cfg.region,
        coordinate_space=cfg.coordinate_space,
        scale=scale_info.scale,
    )
    log(
        f"Display scale={scale_info.scale} ({scale_info.source}); "
        f"coordinate_space={cfg.coordinate_space}; mss_region={mss_region}"
    )

    if grab is None:
        grab = _mss_grab_png
    if advance is None:
        advance = _advance_page

    if cfg.start_delay_sec > 0:
        log(
            f"Starting in {cfg.start_delay_sec}s — focus the 알라딘 eBook window now "
            "(Screen Recording + Accessibility must be enabled)."
        )
        sleep(cfg.start_delay_sec)

    written: list[str] = []
    started = datetime.now(timezone.utc).isoformat()

    for page in range(1, cfg.pages + 1):
        name = page_filename(cfg, page)
        out_path = book_dir / name
        if cfg.save_images or cfg.save_pdf:
            png = grab(mss_region)
            out_path.write_bytes(png)
            written.append(name)
            log(f"Captured {page}/{cfg.pages} -> {out_path}")

        if page < cfg.pages:
            advance(cfg.next_page)
            sleep(cfg.delay_ms / 1000.0)

    manifest = {
        "book_title": cfg.title,
        "pages_requested": cfg.pages,
        "files": written,
        "region_config": asdict(cfg.region),
        "coordinate_space": cfg.coordinate_space,
        "retina_scale": scale_info.to_dict(),
        "mss_region_physical": mss_region,
        "next_page": cfg.next_page,
        "target_os": "macOS",
        "viewer": "알라딘 eBook",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "notice": PERSONAL_USE,
        "upstream_credit": "Capture loop adapted from p0tat0-113/ebookAutoCapture",
    }
    manifest_path = book_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(f"Wrote {manifest_path}")
    return book_dir


def _mss_grab_png(monitor: dict) -> bytes:
    import mss
    import mss.tools

    with mss.mss() as sct:
        shot = sct.grab(monitor)
        return mss.tools.to_png(shot.rgb, shot.size)
