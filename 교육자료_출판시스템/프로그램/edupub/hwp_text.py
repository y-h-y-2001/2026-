"""한글(HWP 5.0) 파일에서 본문 글자를 뽑는다.

교육부 고시문이 한글 파일이라서 필요하다. 글자가 깨져 보이면
그 문장은 성취기준으로 넣지 않는다.
"""

from __future__ import annotations

import struct
import zlib

import olefile

# 확장 컨트롤 뒤에 붙는 8바이트. 한글 문서 파일 형식 5.0의 문단 텍스트.
_EXTRA = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}


def _records(data: bytes) -> list[tuple[int, bytes]]:
    index = 0
    found: list[tuple[int, bytes]] = []
    size = len(data)
    while index + 4 <= size:
        header = struct.unpack_from("<I", data, index)[0]
        index += 4
        tag = header & 0x3FF
        length = (header >> 20) & 0xFFF
        if length == 0xFFF:
            if index + 4 > size:
                break
            length = struct.unpack_from("<I", data, index)[0]
            index += 4
        found.append((tag, data[index : index + length]))
        index += length
    return found


def _paragraph(record: bytes) -> str:
    chars: list[str] = []
    index = 0
    while index + 1 < len(record):
        code = struct.unpack_from("<H", record, index)[0]
        index += 2
        if code in (10, 13):
            chars.append("\n")
        elif code < 32:
            index = _skip_control_payload(record, index, code)
        elif 0xD800 <= code <= 0xDFFF or code in (0xFFFE, 0xFFFF):
            continue
        else:
            chars.append(chr(code))
    return "".join(chars)


def _skip_control_payload(record: bytes, index: int, code: int) -> int:
    """확장 컨트롤 뒤에 붙은 식별자만 건너뛴다.

    식별자는 영문 4글자다. 바로 뒤에 본문이 오면 본문을 지우지 않는다.
    """
    if code not in _EXTRA or index + 8 > len(record):
        return index
    header = record[index : index + 4]
    if all(65 <= byte <= 122 for byte in header):
        return index + 8
    return index


def extract_hwp_text(path) -> str:
    ole = olefile.OleFileIO(str(path))
    try:
        header = ole.openstream("FileHeader").read()
        if not header.startswith(b"HWP Document File"):
            raise ValueError("HWP 5.0 문서가 아닙니다.")
        compressed = bool(struct.unpack_from("<I", header, 36)[0] & 1)
        chunks: list[str] = []
        for entry in ole.listdir():
            if entry[0] != "BodyText":
                continue
            data = ole.openstream("/".join(entry)).read()
            if compressed:
                data = zlib.decompress(data, -15)
            for tag, record in _records(data):
                if tag == 67:
                    chunks.append(_paragraph(record))
        return "\n".join(chunks)
    finally:
        ole.close()
