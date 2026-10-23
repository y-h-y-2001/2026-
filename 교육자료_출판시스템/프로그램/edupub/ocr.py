"""스캔한 쪽의 그림을 글자로 바꾼다. Tesseract와 한글 언어 파일이 필요하다."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pymupdf

from edupub.db import connect, now_seoul
from edupub.paths import EXTRACT_DIR, relative


def ocr_status() -> str:
    program = shutil.which("tesseract")
    if not program:
        return "Tesseract가 설치되어 있지 않습니다."
    import subprocess

    result = subprocess.run([program, "--list-langs"], capture_output=True, text=True, check=False)
    languages = result.stdout + result.stderr
    if "kor" not in languages.split():
        return "Tesseract는 있으나 한글(kor) 언어 파일이 없습니다."
    return "사용 가능"


def ocr_pdf(path: Path) -> Path:
    status = ocr_status()
    if status != "사용 가능":
        raise RuntimeError(
            status
            + " Mac에서는 터미널에 다음을 입력하면 설치할 수 있습니다.\n"
            + "brew install tesseract tesseract-lang\n"
            + "설치는 관리자 권한이 필요할 수 있으니, 설치 전에 내용을 확인해 주세요."
        )
    import pytesseract
    from PIL import Image

    path = path.expanduser().resolve()
    document = pymupdf.open(path)
    pages: list[str] = []
    try:
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            text = pytesseract.image_to_string(image, lang="kor+eng").strip()
            pages.append(f"----- {index}쪽 -----\n{text}")
    finally:
        document.close()
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    out = EXTRACT_DIR / f"{path.stem}_{digest}_OCR.txt"
    out.write_text("\n\n".join(pages), encoding="utf-8")
    _store(path, pages)
    return out


def ocr_image(path: Path) -> str:
    status = ocr_status()
    if status != "사용 가능":
        raise RuntimeError(status)
    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(path), lang="kor+eng").strip()


def _store(path: Path, pages: list[str]) -> None:
    from edupub.paths import DB_PATH

    if not DB_PATH.exists():
        return
    connection = connect()
    try:
        for index, page in enumerate(pages, start=1):
            body = page.split("\n", 1)[-1]
            extraction_id = hashlib.sha256(f"{path}:{index}:ocr:{body}".encode()).hexdigest()[:16]
            connection.execute(
                """
                INSERT OR REPLACE INTO extractions
                (extraction_id, source_path, page_number, method, text, created_on)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (extraction_id, relative(path), index, "ocr", body, now_seoul()),
            )
        connection.commit()
    finally:
        connection.close()
