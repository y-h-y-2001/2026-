"""문항 발문이 같은지, 거의 같은지 찾는다."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from rapidfuzz import fuzz


@dataclass
class DuplicatePair:
    left_id: str
    right_id: str
    score: int
    kind: str
    left_stem: str
    right_stem: str
    left_source: str
    right_source: str


def find_duplicates(connection: sqlite3.Connection, threshold: int = 90) -> list[DuplicatePair]:
    rows = connection.execute(
        """
        SELECT item_id, stem, content_hash, source_id
        FROM items ORDER BY item_id
        """
    ).fetchall()
    found: list[DuplicatePair] = []
    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            if left["content_hash"] == right["content_hash"]:
                score = 100
                kind = "동일"
            else:
                score = int(fuzz.ratio(left["stem"], right["stem"]))
                if score < threshold:
                    continue
                kind = "유사"
            found.append(
                DuplicatePair(
                    left_id=left["item_id"],
                    right_id=right["item_id"],
                    score=score,
                    kind=kind,
                    left_stem=left["stem"],
                    right_stem=right["stem"],
                    left_source=left["source_id"],
                    right_source=right["source_id"],
                )
            )
    found.sort(key=lambda pair: (-pair.score, pair.left_id, pair.right_id))
    return found
