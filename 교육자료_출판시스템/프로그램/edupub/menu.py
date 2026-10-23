"""교사가 터미널에서 고르는 메뉴."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from edupub.build_db import build
from edupub.db import add_item, connect, now_seoul
from edupub.dedupe import find_duplicates
from edupub.docx_out import build_manuscripts
from edupub.ocr import ocr_pdf, ocr_status
from edupub.paths import DB_PATH, INBOX_DIR, TEXTBOOK_DIR, relative
from edupub.pdf_text import extract_pdf


def main() -> None:
    _ensure_database()
    while True:
        print()
        print("교육자료 출판 시스템")
        print("1. 지금 들어 있는 자료 보기")
        print("2. 성취기준 찾기")
        print("3. PDF에서 글자 뽑기")
        print("4. 스캔 PDF 글자 인식")
        print("5. 문항 중복 검사")
        print("6. 학생용·교사용 원고 만들기")
        print("7. 내가 가진 교과서 파일 연결")
        print("8. 비교 메모 적기")
        print("9. 문항 직접 입력")
        print("0. 끝내기")
        choice = input("번호: ").strip()
        try:
            if choice == "1":
                _status()
            elif choice == "2":
                _search()
            elif choice == "3":
                path = Path(input("PDF 경로: ").strip())
                print(extract_pdf(path))
            elif choice == "4":
                print(ocr_status())
                path = Path(input("스캔 PDF 경로: ").strip())
                print(ocr_pdf(path))
            elif choice == "5":
                _duplicates()
            elif choice == "6":
                _manuscript()
            elif choice == "7":
                _link_file()
            elif choice == "8":
                _note()
            elif choice == "9":
                _new_item()
            elif choice == "0":
                print("끝냈습니다.")
                return
            else:
                print("메뉴에 있는 번호를 입력해 주세요.")
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            print(error)


def _ensure_database() -> None:
    if DB_PATH.exists():
        return
    print("처음 실행입니다. 교육과정 고시와 검정 공고를 데이터베이스로 만들고 있습니다.")
    build()
    print("만들었습니다.")


def _status() -> None:
    connection = connect()
    try:
        standard_count = connection.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
        book_count = connection.execute("SELECT COUNT(*) FROM textbooks").fetchone()[0]
        secured = connection.execute("SELECT COUNT(*) FROM textbooks WHERE content_secured = 1").fetchone()[0]
        item_count = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        print(f"성취기준 {standard_count}개")
        print(f"교과서 서지 {book_count}종 (이 가운데 원문 파일을 연결한 도서 {secured}종)")
        print(f"문항 {item_count}개")
        print("교과서 본문은 들어 있지 않습니다. 검정 공고에서 확인한 서명·발행사·검정번호만 있습니다.")
    finally:
        connection.close()


def _search() -> None:
    keyword = input("코드 또는 찾을 말: ").strip()
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT code, school_level, subject, unit_title, statement
            FROM standards
            WHERE code LIKE ? OR statement LIKE ? OR unit_title LIKE ? OR subject LIKE ?
            ORDER BY code LIMIT 30
            """,
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        print("해당하는 성취기준이 없습니다.")
        return
    for row in rows:
        print(f"{row['code']} | {row['school_level']} {row['subject']} | {row['unit_title']}")
        print(f"  {row['statement']}")


def _duplicates() -> None:
    connection = connect()
    try:
        pairs = find_duplicates(connection)
    finally:
        connection.close()
    if not pairs:
        print("겹치는 문항이 없습니다.")
        return
    for pair in pairs:
        print(f"[{pair.kind} {pair.score}] {pair.left_id} ↔ {pair.right_id}")
        print(f"  {pair.left_stem}")
        if pair.kind != "동일":
            print(f"  {pair.right_stem}")
        print(f"  출처 {pair.left_source} / {pair.right_source}")


def _manuscript() -> None:
    connection = connect()
    try:
        student, teacher = build_manuscripts(connection)
    finally:
        connection.close()
    print(f"학생용: {student}")
    print(f"교사용: {teacher}")


def _link_file() -> None:
    approval = input("검정번호 (예: 중10528-P-01): ").strip()
    source = Path(input("가지고 있는 PDF 경로: ").strip()).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"파일이 없습니다: {source}")
    TEXTBOOK_DIR.mkdir(parents=True, exist_ok=True)
    destination = TEXTBOOK_DIR / f"{approval}_{source.name}"
    if destination.exists():
        raise FileExistsError(f"이미 같은 이름의 파일이 있어 덮어쓰지 않았습니다: {destination}")
    shutil.copy2(source, destination)
    from edupub.db import file_sha256

    connection = connect()
    try:
        row = connection.execute(
            "SELECT textbook_id FROM textbooks WHERE approval_number = ?",
            (approval,),
        ).fetchone()
        if row is None:
            destination.unlink()
            raise ValueError(f"공고에서 확인되지 않은 검정번호입니다: {approval}")
        connection.execute(
            """
            UPDATE textbooks
            SET content_secured = 1, local_path = ?, file_sha256 = ?
            WHERE approval_number = ?
            """,
            (relative(destination), file_sha256(destination), approval),
        )
        connection.commit()
    finally:
        connection.close()
    print(f"연결했습니다. 파일은 이 폴더 안에만 둡니다: {destination}")
    print("교과서 본문은 깃 저장소에 올리지 않도록 제외해 두었습니다.")


def _note() -> None:
    code = input("성취기준 코드: ").strip()
    approval = input("검정번호: ").strip()
    page = input("쪽 (모르면 비워 두기): ").strip() or "쪽 미기재"
    note = input("내 메모 (교과서 문장을 통째로 붙이지 않기): ").strip()
    if len(note) > 400:
        raise ValueError("메모가 너무 깁니다. 관찰한 점을 짧게 적고, 교과서 문장 전재는 피합니다.")
    if not note:
        raise ValueError("메모가 비어 있습니다.")
    connection = connect()
    try:
        standard = connection.execute("SELECT code FROM standards WHERE code = ?", (code,)).fetchone()
        book = connection.execute(
            "SELECT textbook_id FROM textbooks WHERE approval_number = ?",
            (approval,),
        ).fetchone()
        if standard is None:
            raise ValueError(f"없는 성취기준입니다: {code}")
        if book is None:
            raise ValueError(f"없는 검정번호입니다: {approval}")
        comparison_id = f"CMP-{code}-{approval}-{now_seoul().replace(' ', '').replace(':', '')}"
        connection.execute(
            """
            INSERT INTO comparisons (
                comparison_id, standard_code, textbook_id, note, page_ref, note_kind, recorded_on
            ) VALUES (?, ?, ?, ?, ?, '교사메모', ?)
            """,
            (comparison_id, code, book["textbook_id"], note, page, now_seoul()),
        )
        connection.commit()
    finally:
        connection.close()
    print("메모를 저장했습니다. 교사용 원고를 만들면 이 성취기준 아래에 붙습니다.")


def _new_item() -> None:
    print("성취기준 코드와 출처가 있어야 문항을 넣을 수 있습니다.")
    code = input("성취기준 코드: ").strip()
    stem = input("발문: ").strip()
    answer = input("정답: ").strip()
    explanation = input("해설: ").strip()
    raw_choices = input("선택지 (줄 바꿈 대신 | 로 구분, 없으면 엔터): ").strip()
    choices = [part.strip() for part in raw_choices.split("|") if part.strip()]
    connection = connect()
    try:
        count = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0] + 1
        add_item(
            connection,
            item_id=f"ITEM-{count:04d}",
            stem=stem,
            choices=choices,
            answer=answer,
            explanation=explanation,
            item_type="선택형" if choices else "서술형",
            standard_code=code,
            source_id="SRC-교사작성",
            origin="교사작성",
        )
        connection.commit()
    finally:
        connection.close()
    print("저장했습니다. 직접 만든 문항의 출처 종류는 교사작성입니다.")


def inbox_hint() -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"inbox": str(INBOX_DIR)}, ensure_ascii=False))
