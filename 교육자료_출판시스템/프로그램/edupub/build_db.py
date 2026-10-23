"""확인한 원문에서 데이터베이스를 다시 만든다.

이미 있는 데이터베이스 파일은 지우지 않고, 이름 뒤에 시각을 붙여 보관한다.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from edupub.curriculum import parse_standards
from edupub.db import connect, export_tables, file_sha256, initialize, now_seoul
from edupub.hwp_text import extract_hwp_text
from edupub.paths import (
    CURRICULUM_HWP,
    DB_PATH,
    HIGH_APPROVAL_PDF,
    MIDDLE_APPROVAL_PDF,
    SAMPLE_DIR,
    relative,
)
from edupub.textbooks import parse_approval_pdf

DISPLAY_TITLES = {
    "사회①": "사회 ①",
    "사회②": "사회 ②",
    "사회과부도": "사회과 부도",
    "역사①": "역사 ①",
    "역사②": "역사 ②",
    "역사부도": "역사 부도",
    "한국사1": "한국사1",
    "한국사2": "한국사2",
    "통합사회1": "통합사회1",
    "통합사회2": "통합사회2",
    "세계시민과지리": "세계시민과 지리",
    "세계사": "세계사",
    "사회와문화": "사회와 문화",
    "지리부도": "지리 부도",
}

CURRICULUM_SOURCE = "SRC-2022-33-별책7"
MIDDLE_SOURCE = "SRC-KICE-2024-중학교-검정공고"
HIGH_SOURCE = "SRC-KICE-2024-고등학교-검정공고"
SAMPLE_SOURCE = "SRC-자체작성-샘플"


def build() -> None:
    _archive_existing()
    connection = connect()
    try:
        initialize(connection)
        _sources(connection)
        text = extract_hwp_text(CURRICULUM_HWP)
        standards = parse_standards(text)
        if len(standards) < 300:
            raise RuntimeError(f"성취기준이 너무 적습니다. 원문 해석을 멈추고 확인이 필요합니다: {len(standards)}개")
        for standard in standards:
            connection.execute(
                """
                INSERT INTO standards (
                    code, school_level, subject, course_group, domain, unit_title,
                    statement, commentary, source_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    standard.code,
                    standard.school_level,
                    standard.subject,
                    standard.course_group,
                    standard.domain,
                    standard.unit_title,
                    standard.statement,
                    standard.commentary,
                    CURRICULUM_SOURCE,
                ),
            )
        _textbooks(connection, MIDDLE_APPROVAL_PDF, MIDDLE_SOURCE)
        _textbooks(connection, HIGH_APPROVAL_PDF, HIGH_SOURCE)
        _sample_items(connection)
        connection.commit()
        export_tables(connection)
    finally:
        connection.close()


def _archive_existing() -> None:
    if not DB_PATH.exists():
        return
    stamp = now_seoul().replace(":", "").replace(" ", "_")
    kept = DB_PATH.with_name(f"출판시스템_이전_{stamp}.sqlite")
    shutil.move(DB_PATH, kept)


def _sources(connection) -> None:
    rows = [
        (
            CURRICULUM_SOURCE,
            "교육과정고시",
            "[별책 7] 사회과 교육과정",
            "교육부",
            "교육부 고시 제2022-33호",
            "2022-12-22",
            "2026-10-23",
            "https://www.moe.go.kr/boardCnts/viewRenew.do?boardID=141&boardSeq=93458&lev=0&m=0404",
            relative(CURRICULUM_HWP),
            file_sha256(CURRICULUM_HWP),
            "국가가 고시한 교육과정 원문이다. 출처를 밝혀 수록했다.",
            "원문파일대조",
            "교육부 게시판 boardSeq=93458 붙임2 압축파일에서 2026-10-23에 받았다. "
            "압축 안 한글 파일의 시각은 2023-11-13이다. "
            "국가교육위원회 고시 제2024-3호(2024-08-16)는 교육부 고시 제2022-33호를 일부개정하면서 "
            "사회과 교육과정은 별책 7에 따른다고 밝힌다. 그 개정으로 바뀐 별책 7 파일을 "
            "이 작업에서 별도로 확보하지 못했다. 성취기준 문장은 위 한글 파일 기준이다.",
        ),
        (
            MIDDLE_SOURCE,
            "검정합격공고",
            "2024년 교과용도서 검정 최종 합격 공고(중학교)",
            "한국교육과정평가원",
            "2024년 교과용도서 검정 합격 결정 공고",
            "2024-08-30",
            "2026-10-23",
            "https://tbh.kice.re.kr/inf/if001View.do",
            relative(MIDDLE_APPROVAL_PDF),
            file_sha256(MIDDLE_APPROVAL_PDF),
            "검정 합격 공고의 서지 정보만 수록했다. 교과서 본문은 포함하지 않았다.",
            "공고원문대조_본문미확보",
            "한국교육과정평가원 교과서검정 공지 번호 378의 첨부 압축파일 중 중학교 합격 공고 PDF다.",
        ),
        (
            HIGH_SOURCE,
            "검정합격공고",
            "2024년 교과용도서 검정 최종 합격 공고(고등학교)",
            "한국교육과정평가원",
            "2024년 교과용도서 검정 합격 결정 공고",
            "2024-08-30",
            "2026-10-23",
            "https://tbh.kice.re.kr/inf/if001View.do",
            relative(HIGH_APPROVAL_PDF),
            file_sha256(HIGH_APPROVAL_PDF),
            "검정 합격 공고의 서지 정보만 수록했다. 교과서 본문은 포함하지 않았다.",
            "공고원문대조_본문미확보",
            "같은 공지 번호 378의 고등학교 합격 공고 PDF다. "
            "2025년 합격 공고와 2026년 합격 공고(공지 505, 514, 540)를 열어 보았으나 "
            "중·고등학교 사회·역사 도서는 없었다. 2026년 공고는 중학교 국어·영어였고, "
            "2025년 2차 자료는 초등학교 사회였다. 그 도서는 이 데이터베이스에 넣지 않았다.",
        ),
        (
            SAMPLE_SOURCE,
            "자체작성",
            "시스템 점검용 자체 문항",
            "교육자료 출판 시스템",
            "",
            "2026-10-23",
            "2026-10-23",
            "",
            relative(SAMPLE_DIR / "문항_샘플.json"),
            file_sha256(SAMPLE_DIR / "문항_샘플.json"),
            "교과서에서 옮기지 않은 예시 문항이다.",
            "자체작성",
            "프로그램이 정상 작동하는지 확인하는 데만 쓴다. 수업 배포용 문항으로 보지 않는다.",
        ),
        (
            "SRC-교사작성",
            "자체작성",
            "교사가 이 프로그램에 직접 입력한 문항",
            "사용자",
            "",
            "",
            "2026-10-23",
            "",
            "",
            "",
            "교사가 직접 쓴 문장만 넣는다. 교과서 문장을 붙여 넣지 않는다.",
            "교사입력",
            "메뉴에서 문항을 추가하면 이 출처로 기록된다.",
        ),
    ]
    connection.executemany(
        """
        INSERT INTO sources (
            source_id, source_type, title, issuer, document_number, published_on,
            retrieved_on, url, local_path, sha256, rights_note, verification_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _textbooks(connection, pdf: Path, source_id: str) -> None:
    records = parse_approval_pdf(pdf)
    if not records:
        raise RuntimeError(f"공고에서 사회·역사 도서를 읽지 못했습니다: {pdf.name}")
    for record in records:
        connection.execute(
            """
            INSERT INTO textbooks (
                textbook_id, school_level, title, publisher, lead_author, approval_date,
                approval_number, page_count, bibliography_source_id, content_secured,
                local_path, file_sha256, source_page, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '', '', ?, ?)
            """,
            (
                "TB-" + record.approval_number,
                record.school_level,
                DISPLAY_TITLES[record.title],
                record.publisher,
                record.lead_author,
                record.approval_date,
                record.approval_number,
                record.page_count,
                source_id,
                record.source_page,
                "본문 미확보. 검정 합격 공고의 서지 정보만 등록했다. "
                "대표 저자 칸이 비어 있으면 공고 표에서 그 칸을 읽지 못한 것이다.",
            ),
        )


def _sample_items(connection) -> None:
    payload = json.loads((SAMPLE_DIR / "문항_샘플.json").read_text(encoding="utf-8"))
    from edupub.db import add_item

    for item in payload["items"]:
        add_item(
            connection,
            item_id=item["item_id"],
            stem=item["stem"],
            choices=item["choices"],
            answer=item["answer"],
            explanation=item["explanation"],
            item_type=item["item_type"],
            standard_code=item["standard_code"],
            source_id=SAMPLE_SOURCE,
            origin=item["origin"],
        )


if __name__ == "__main__":
    build()
    print(f"데이터베이스를 만들었습니다: {DB_PATH}")
