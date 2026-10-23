#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edupub.build_db import build
from edupub.paths import DB_PATH

if __name__ == "__main__":
    build()
    print(f"만들었습니다: {DB_PATH}")
