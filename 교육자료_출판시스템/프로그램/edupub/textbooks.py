"""검정 합격 공고 PDF에서 사회·역사 교과서의 서지 정보만 읽는다.

교과서 본문은 읽지 않는다. 공고 표의 도서명, 검정번호, 발행사,
대표 저자 칸만 가져온다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

# 2022 개정 사회과 과목 가운데 2024년 합격 공고에서 표 제목으로
# 확인한 것만 남긴다. 제목이 이 목록과 같아야 넣는다.
ALLOWED_TITLES = {
    "사회①",
    "사회②",
    "사회과부도",
    "역사①",
    "역사②",
    "역사부도",
    "한국사1",
    "한국사2",
    "통합사회1",
    "통합사회2",
    "세계시민과지리",
    "세계사",
    "사회와문화",
    "지리부도",
}

_VOLUME = re.compile(r"^([①②③④⑤⑥⑦⑧⑨])(\d{4}\.?)$")
_HANGUL_NAME = re.compile(r"^[가-힣]{2,5}$")


@dataclass
class TextbookRecord:
    school_level: str
    title: str
    publisher: str
    lead_author: str
    approval_date: str
    approval_number: str
    page_count: str
    source_pdf: str
    source_page: int


def _compact_title(tokens: list[str]) -> str:
    volume = ""
    parts: list[str] = []
    for token in tokens:
        volume_match = _VOLUME.fullmatch(token)
        if volume_match:
            volume = volume_match.group(1)
            continue
        token = re.sub(r"\d{4}\.?$", "", token)
        if token and token not in {"2024.", "8.30."}:
            parts.append(token)
    title = "".join(parts)
    if volume and not title.endswith(volume):
        title += volume
    if len(title) >= 2 and len(title) % 2 == 0:
        half = len(title) // 2
        if title[:half] == title[half:]:
            return ""
    return title


def _clean_publisher(tokens: list[str]) -> str:
    raw = "".join(tokens)
    raw = re.sub(r"[\s,]+", "", raw)
    raw = raw.replace("㈜", "(주)")
    raw = re.sub(r"\(주([^)]+)\)", r"(주)\1", raw)
    if raw.startswith("주식회사"):
        raw = "주식회사 " + raw.removeprefix("주식회사")
    elif "(주)" not in raw and raw.startswith("주") and len(raw) > 2:
        raw = "(주)" + raw[1:]
    company_marks = len(re.findall(r"\(주\)|주식회사", raw))
    if company_marks != 1 or not re.search(r"[가-힣]", raw):
        return ""
    return raw


def _records_on_page(page: pymupdf.Page, page_number: int, pdf_name: str) -> list[TextbookRecord]:
    words = page.get_text("words")
    starters = [
        word
        for word in words
        if 88 <= word[0] < 125 and re.fullmatch(r"[중고]\d{4,5}", word[4])
    ]
    starters.sort(key=lambda word: word[1])
    records: list[TextbookRecord] = []
    for index, starter in enumerate(starters):
        top = starter[1] - 2
        next_top = starters[index + 1][1] - 2 if index + 1 < len(starters) else 10000
        bottom = next_top

        def column(left: float, right: float, limit: float | None = None) -> list[str]:
            lower = top
            upper = bottom if limit is None else min(bottom, starter[1] + limit)
            picked = [word for word in words if left <= word[0] < right and lower <= word[1] < upper]
            picked.sort(key=lambda word: (word[1], word[0]))
            return [word[4] for word in picked]

        approval = "".join(column(88, 125, 40))
        if not re.fullmatch(r"[중고]\d{5}-[A-Z]-\d{2}", approval):
            continue
        title = _compact_title(column(0, 74))
        if title not in ALLOWED_TITLES:
            continue
        publisher = _clean_publisher(column(438, 476))
        if not publisher:
            continue
        date_bits: list[str] = []
        for token in column(0, 96, 28):
            volume_match = _VOLUME.fullmatch(token)
            if volume_match:
                date_bits.append(volume_match.group(2))
            elif re.fullmatch(r"\d{4}\.?|\d{1,2}\.\d{1,2}\.?", token):
                date_bits.append(token)
        pages = ""
        for token in column(145, 170, 24):
            if re.fullmatch(r"\d{2,4}", token):
                pages = token
                break
        lead = ""
        for token in column(350, 390, 40):
            if _HANGUL_NAME.fullmatch(token):
                lead = token
                break
        level = "중학교" if approval.startswith("중") else "고등학교"
        date = "".join(date_bits).replace("..", ".")
        if re.fullmatch(r"\d{4}\.\d{1,2}\.\d{1,2}\.?", date):
            date = date.rstrip(".")
        else:
            date = ""
        records.append(
            TextbookRecord(
                school_level=level,
                title=title,
                publisher=publisher,
                lead_author=lead,
                approval_date=date,
                approval_number=approval,
                page_count=pages,
                source_pdf=pdf_name,
                source_page=page_number,
            )
        )
    return records


def parse_approval_pdf(path: Path) -> list[TextbookRecord]:
    document = pymupdf.open(path)
    found: list[TextbookRecord] = []
    try:
        for index, page in enumerate(document):
            found.extend(_records_on_page(page, index + 1, path.name))
    finally:
        document.close()
    # 같은 검정번호는 한 번만
    unique: dict[str, TextbookRecord] = {}
    for record in found:
        unique.setdefault(record.approval_number, record)
    return list(unique.values())
