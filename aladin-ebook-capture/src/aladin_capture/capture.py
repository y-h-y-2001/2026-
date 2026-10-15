"""Region screenshot + page-advance loop.

Adapted from p0tat0-113/ebookAutoCapture (Tkinter GUI Capture class).
This module is GUI-free so CLI / agents can drive it.
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
    elif mode == "click":
        pyautogui.click()
    else:
        raise ValueError(f"Unknown next_page mode: {mode}")


def page_filename(cfg: CaptureConfig, page: int) -> str:
    return f"page-{page:0{cfg.zero_pad}d}.png"


def dry_run_plan(cfg: CaptureConfig) -> dict:
    """Describe what capture would do without touching the screen."""
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
        "book_title": cfg.title,
        "pages": cfg.pages,
        "region": asdict(cfg.region),
        "delay_ms": cfg.delay_ms,
        "start_delay_sec": cfg.start_delay_sec,
        "next_page": cfg.next_page,
        "book_dir": str(cfg.book_dir.resolve()),
        "save_images": cfg.save_images,
        "save_pdf": cfg.save_pdf,
        "planned_files": pages,
        "notice": PERSONAL_USE,
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

    Inject grab/advance/sleep for tests. On a real run, grab uses mss and
    advance uses pyautogui (Windows desktop with Aladin viewer focused).
    """
    log = log or (lambda msg: print(msg, file=sys.stderr))

    if cfg.personal_use_notice:
        log(PERSONAL_USE)

    if dry_run:
        plan = dry_run_plan(cfg)
        log(json.dumps(plan, indent=2, ensure_ascii=False))
        return cfg.book_dir

    book_dir = cfg.book_dir
    book_dir.mkdir(parents=True, exist_ok=True)

    if grab is None:
        grab = _mss_grab_png
    if advance is None:
        advance = _advance_page

    if cfg.start_delay_sec > 0:
        log(f"Starting in {cfg.start_delay_sec}s — focus the Aladin viewer window now.")
        sleep(cfg.start_delay_sec)

    written: list[str] = []
    started = datetime.now(timezone.utc).isoformat()

    for page in range(1, cfg.pages + 1):
        name = page_filename(cfg, page)
        out_path = book_dir / name
        if cfg.save_images or cfg.save_pdf:
            png = grab(cfg.region.as_mss_monitor())
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
        "region": asdict(cfg.region),
        "next_page": cfg.next_page,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "notice": PERSONAL_USE,
        "upstream_credit": "Capture loop adapted from p0tat0-113/ebookAutoCapture",
    }
    manifest_path = book_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"Wrote {manifest_path}")
    return book_dir


def _mss_grab_png(monitor: dict) -> bytes:
    import mss
    import mss.tools

    with mss.mss() as sct:
        shot = sct.grab(monitor)
        return mss.tools.to_png(shot.rgb, shot.size)
