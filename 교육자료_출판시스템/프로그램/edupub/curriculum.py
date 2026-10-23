"""2022 개정 사회과 교육과정 한글 파일에서 성취기준만 고른다."""

from __future__ import annotations

import re
from dataclasses import dataclass

# 별책 7 차림표에 있는 과목 제목. 본문에서 '1. 성격 및 목표' 바로 앞
# 제목으로 확인된 것만 쓴다.
SECTIONS: list[tuple[str, str]] = [
    ("사회", "공통 교육과정"),
    ("역사", "공통 교육과정"),
    ("한국사1, 한국사2", "선택 중심 교육과정·공통 과목"),
    ("통합사회1, 통합사회2", "선택 중심 교육과정·공통 과목"),
    ("세계시민과 지리", "선택 중심 교육과정·일반 선택"),
    ("세계사", "선택 중심 교육과정·일반 선택"),
    ("사회와 문화", "선택 중심 교육과정·일반 선택"),
    ("한국지리 탐구", "선택 중심 교육과정·진로 선택"),
    ("도시의 미래 탐구", "선택 중심 교육과정·진로 선택"),
    ("동아시아 역사 기행", "선택 중심 교육과정·진로 선택"),
    ("정치", "선택 중심 교육과정·진로 선택"),
    ("법과 사회", "선택 중심 교육과정·진로 선택"),
    ("경제", "선택 중심 교육과정·진로 선택"),
    ("국제 관계의 이해", "선택 중심 교육과정·진로 선택"),
    ("여행지리", "선택 중심 교육과정·융합 선택"),
    ("역사로 탐구하는 현대 세계", "선택 중심 교육과정·융합 선택"),
    ("사회문제 탐구", "선택 중심 교육과정·융합 선택"),
    ("금융과 경제생활", "선택 중심 교육과정·융합 선택"),
    ("기후변화와 지속가능한 세계", "선택 중심 교육과정·융합 선택"),
]

_CODE = re.compile(
    r"\[(?P<code>\d{1,2}[가-힣]{1,8}(?:\([가-힣]{1,8}\))?\d{0,2}-\d{2}(?:-\d{2})?)\]"
)
_UNIT = re.compile(r"^\((\d+)\)\s*(.+)$")
_DASHES = str.maketrans({"–": "-", "—": "-", "−": "-", "‒": "-"})


@dataclass
class Standard:
    code: str
    school_level: str
    subject: str
    course_group: str
    domain: str
    unit_title: str
    statement: str
    commentary: str


def normalize_code(code: str) -> str:
    return code.translate(_DASHES).replace(" ", "")


def _school_and_subject(section: str, code: str) -> tuple[str, str]:
    if section == "사회":
        if code.startswith(("4", "6")):
            return "초등학교", "사회"
        if code.startswith("9"):
            return "중학교", "사회"
        return "미분류", "사회"
    if section == "역사":
        return "중학교", "역사"
    return "고등학교", section


def _domain(code: str) -> str:
    match = re.search(r"\(([^)]+)\)", code)
    return match.group(1) if match else ""


def find_sections(text: str) -> list[tuple[int, str, str]]:
    found: list[tuple[int, str, str]] = []
    missing: list[str] = []
    for title, group in SECTIONS:
        pattern = re.compile(rf"(?:^|\n){re.escape(title)}\n")
        hit = None
        for match in pattern.finditer(text):
            window = text[match.end() : match.end() + 8000]
            if "1. 성격 및 목표" in window:
                hit = match.start()
                break
        if hit is None:
            missing.append(title)
        else:
            found.append((hit, title, group))
    if missing:
        raise ValueError("교육과정 원문에서 과목 제목을 찾지 못했습니다: " + ", ".join(missing))
    found.sort()
    return found


def _clean_statement(text: str) -> str:
    text = text.translate(_DASHES)
    text = re.split(r"\n\s*\((?:가|나|다)\)", text, maxsplit=1)[0]
    text = re.split(r"\n\s*\(\d+\)", text, maxsplit=1)[0]
    text = re.split(r"\n\s*(?:나\. 성취기준|3\. 교수)", text, maxsplit=1)[0]
    text = re.sub(r"\s+", " ", text).strip(" \n\t·")
    return text


def parse_standards(text: str) -> list[Standard]:
    text = text.translate(_DASHES)
    return _walk_sections(text, find_sections(text))


def _walk_sections(text: str, sections: list[tuple[int, str, str]]) -> list[Standard]:
    standards: dict[str, Standard] = {}
    for index, (start, title, group) in enumerate(sections):
        end = sections[index + 1][0] if index + 1 < len(sections) else len(text)
        body = text[start:end]
        mode = "other"
        unit = ""
        current = ""
        pieces: list[str] = []

        def commit() -> None:
            nonlocal current, pieces
            if not current:
                pieces = []
                return
            cleaned = _clean_statement("".join(pieces))
            pieces = []
            code = current
            current = ""
            if mode == "statement":
                if not (8 <= len(cleaned) <= 800):
                    return
                if cleaned.startswith(("은 ", "는 ", "이 ", "가 ", "을 ", "를 ", "에서는")):
                    return
                school, subject = _school_and_subject(title, code)
                if code not in standards:
                    standards[code] = Standard(
                        code=code,
                        school_level=school,
                        subject=subject,
                        course_group=group,
                        domain=_domain(code),
                        unit_title=unit,
                        statement=cleaned,
                        commentary="",
                    )
            elif mode == "commentary" and code in standards and cleaned:
                if not standards[code].commentary:
                    standards[code].commentary = cleaned

        lines = body.splitlines()
        for line in lines:
            stripped = line.strip()
            if "나. 성취기준" in stripped:
                commit()
                mode = "statement"
                continue
            if "성취기준 해설" in stripped:
                commit()
                mode = "commentary"
                continue
            if "적용 시 고려" in stripped:
                commit()
                mode = "apply"
                continue
            unit_match = _UNIT.match(stripped)
            if unit_match and "[" not in stripped:
                commit()
                mode = "statement"
                unit = unit_match.group(2).strip() or unit
                continue
            if mode not in {"statement", "commentary"}:
                continue
            position = 0
            matches = list(_CODE.finditer(line))
            if not matches:
                pieces.append(line + "\n")
                continue
            for match in matches:
                pieces.append(line[position : match.start()])
                commit()
                current = normalize_code(match.group("code"))
                pieces = []
                position = match.end()
            pieces.append(line[position:] + "\n")
        commit()
    return [standards[key] for key in sorted(standards)]
