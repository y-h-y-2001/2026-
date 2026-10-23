"""출처, 성취기준, 교과서 서지, 문항을 한 파일에 보관한다."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from edupub.paths import DB_DIR, DB_PATH

SEOUL = ZoneInfo("Asia/Seoul")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    issuer TEXT,
    document_number TEXT,
    published_on TEXT,
    retrieved_on TEXT,
    url TEXT,
    local_path TEXT,
    sha256 TEXT,
    rights_note TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS standards (
    code TEXT PRIMARY KEY,
    school_level TEXT NOT NULL,
    subject TEXT NOT NULL,
    course_group TEXT NOT NULL,
    domain TEXT NOT NULL,
    unit_title TEXT NOT NULL,
    statement TEXT NOT NULL,
    commentary TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS textbooks (
    textbook_id TEXT PRIMARY KEY,
    school_level TEXT NOT NULL,
    title TEXT NOT NULL,
    publisher TEXT NOT NULL,
    lead_author TEXT NOT NULL,
    approval_date TEXT NOT NULL,
    approval_number TEXT NOT NULL UNIQUE,
    page_count TEXT NOT NULL,
    bibliography_source_id TEXT NOT NULL REFERENCES sources(source_id),
    content_secured INTEGER NOT NULL DEFAULT 0,
    local_path TEXT,
    file_sha256 TEXT,
    source_page INTEGER NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comparisons (
    comparison_id TEXT PRIMARY KEY,
    standard_code TEXT NOT NULL REFERENCES standards(code),
    textbook_id TEXT NOT NULL REFERENCES textbooks(textbook_id),
    note TEXT NOT NULL,
    page_ref TEXT NOT NULL,
    note_kind TEXT NOT NULL,
    recorded_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    stem TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    item_type TEXT NOT NULL,
    standard_code TEXT NOT NULL REFERENCES standards(code),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    origin TEXT NOT NULL,
    normalized TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extractions (
    extraction_id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    method TEXT NOT NULL,
    text TEXT NOT NULL,
    created_on TEXT NOT NULL
);
"""


def now_seoul() -> str:
    return datetime.now(SEOUL).strftime("%Y-%m-%d %H:%M")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def connect() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def normalize_stem(text: str) -> str:
    import re

    compact = re.sub(r"\s+", "", text)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", compact).lower()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_stem(text).encode("utf-8")).hexdigest()


def require_standard(connection: sqlite3.Connection, code: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM standards WHERE code = ?", (code,)).fetchone()
    if row is None:
        raise ValueError(f"데이터베이스에 없는 성취기준입니다: {code}")
    return row


def require_source(connection: sqlite3.Connection, source_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,)).fetchone()
    if row is None:
        raise ValueError(f"데이터베이스에 없는 출처입니다: {source_id}")
    return row


def add_item(
    connection: sqlite3.Connection,
    *,
    item_id: str,
    stem: str,
    choices: list[str],
    answer: str,
    explanation: str,
    item_type: str,
    standard_code: str,
    source_id: str,
    origin: str,
) -> None:
    require_standard(connection, standard_code)
    require_source(connection, source_id)
    if not stem.strip():
        raise ValueError("문항 발문이 비어 있습니다.")
    normalized = normalize_stem(stem)
    connection.execute(
        """
        INSERT INTO items (
            item_id, stem, choices_json, answer, explanation, item_type,
            standard_code, source_id, origin, normalized, content_hash, created_on
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            stem.strip(),
            json.dumps(choices, ensure_ascii=False),
            answer.strip(),
            explanation.strip(),
            item_type,
            standard_code,
            source_id,
            origin,
            normalized,
            content_hash(stem),
            now_seoul(),
        ),
    )


def export_tables(connection: sqlite3.Connection) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(
        DB_DIR / "성취기준.csv",
        connection.execute(
            """
            SELECT code, school_level, subject, course_group, domain, unit_title, statement, source_id
            FROM standards ORDER BY school_level, subject, code
            """
        ),
        ["성취기준코드", "학교급", "과목", "교육과정구분", "영역", "단원", "성취기준", "출처ID"],
    )
    _write_csv(
        DB_DIR / "교과서_서지.csv",
        connection.execute(
            """
            SELECT school_level, title, publisher, lead_author, approval_date,
                   approval_number, page_count, content_secured, bibliography_source_id, notes
            FROM textbooks ORDER BY school_level, title, publisher
            """
        ),
        ["학교급", "도서명", "발행사", "대표저자", "검정일", "검정번호", "쪽수", "본문확보", "출처ID", "비고"],
    )
    _write_csv(
        DB_DIR / "출처.csv",
        connection.execute(
            """
            SELECT source_id, source_type, title, issuer, document_number, published_on,
                   retrieved_on, url, local_path, sha256, verification_status
            FROM sources ORDER BY source_id
            """
        ),
        ["출처ID", "종류", "제목", "발행처", "문서번호", "공포일", "확인일", "주소", "파일", "SHA256", "확인상태"],
    )


def _write_csv(path: Path, rows: sqlite3.Cursor, headers: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(tuple(row) for row in rows)
