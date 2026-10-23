"""프로젝트 안의 폴더 위치."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = ROOT / "프로그램"
ORIGINAL = ROOT / "원본자료"
CURRICULUM_DIR = ORIGINAL / "교육과정"
APPROVAL_DIR = ORIGINAL / "검정공고"
TEXTBOOK_DIR = ORIGINAL / "교과서"
INBOX_DIR = ORIGINAL / "입고"
EXTRACT_DIR = ORIGINAL / "추출텍스트"
DB_DIR = ROOT / "데이터베이스"
DB_PATH = DB_DIR / "출판시스템.sqlite"
SAMPLE_DIR = ROOT / "샘플"
OUTPUT_DIR = ROOT / "산출물"
STUDENT_OUT = OUTPUT_DIR / "학생용"
TEACHER_OUT = OUTPUT_DIR / "교사용"
VERIFY_DIR = ROOT / "검증"

CURRICULUM_HWP = CURRICULUM_DIR / "[별책7] 사회과 교육과정.hwp"
MIDDLE_APPROVAL_PDF = APPROVAL_DIR / "2024년_교과용도서_검정_최종_합격_공고_중학교.pdf"
HIGH_APPROVAL_PDF = APPROVAL_DIR / "2024년_교과용도서_검정_최종_합격_공고_고등학교.pdf"


def relative(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
