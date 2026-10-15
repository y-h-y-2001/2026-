"""Assemble a PDF from captured page PNGs."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from .config import CaptureConfig
from .capture import page_filename


def list_page_images(book_dir: Path, cfg: CaptureConfig) -> list[Path]:
    paths: list[Path] = []
    for page in range(1, cfg.pages + 1):
        path = book_dir / page_filename(cfg, page)
        if path.is_file():
            paths.append(path)
    if not paths:
        # Fallback: any page-*.png sorted
        paths = sorted(book_dir.glob("page-*.png"))
    return paths


def export_pdf(
    cfg: CaptureConfig,
    book_dir: Path | None = None,
    *,
    log: Callable[[str], None] | None = None,
) -> Path:
    log = log or (lambda msg: print(msg, file=sys.stderr))
    book_dir = book_dir or cfg.book_dir
    images = list_page_images(book_dir, cfg)
    if not images:
        raise FileNotFoundError(f"No page-*.png images found under {book_dir}")

    try:
        import img2pdf
    except ImportError as exc:
        raise RuntimeError(
            "img2pdf is required for PDF export. Install: pip install img2pdf"
        ) from exc

    out = book_dir / f"{cfg.book_dir.name}.pdf"
    with out.open("wb") as fh:
        fh.write(img2pdf.convert([str(p) for p in images]))
    log(f"Wrote PDF ({len(images)} pages) -> {out}")
    return out
