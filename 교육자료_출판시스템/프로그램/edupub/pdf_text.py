"""PDF에서 글자 층을 뽑는다. 스캔 그림만 있는 쪽은 OCR로 넘긴다."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf

from edupub.db import connect, now_seoul
from edupub.paths import EXTRACT_DIR, relative


def extract_pdf(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"파일이 없습니다: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("PDF 파일만 넣을 수 있습니다.")
    document = pymupdf.open(path)
    pages: list[str] = []
    try:
        if document.page_count == 0:
            raise ValueError("페이지가 없는 PDF입니다.")
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            pages.append(f"----- {index}쪽 -----\n{text if text else '[이 쪽은 글자 층이 없습니다. OCR을 사용하세요.]'}")
    finally:
        document.close()
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    out = EXTRACT_DIR / f"{path.stem}_{digest}_텍스트.txt"
    out.write_text("\n\n".join(pages), encoding="utf-8")
    _store(path, pages, "pdf_text")
    return out


def _store(path: Path, pages: list[str], method: str) -> None:
    if not _db_ready():
        return
    connection = connect()
    try:
        for index, page in enumerate(pages, start=1):
            body = page.split("\n", 1)[-1]
            extraction_id = hashlib.sha256(f"{path}:{index}:{method}:{body}".encode()).hexdigest()[:16]
            connection.execute(
                """
                INSERT OR REPLACE INTO extractions
                (extraction_id, source_path, page_number, method, text, created_on)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (extraction_id, relative(path), index, method, body, now_seoul()),
            )
        connection.commit()
    finally:
        connection.close()


def _db_ready() -> bool:
    from edupub.paths import DB_PATH

    return DB_PATH.exists()
