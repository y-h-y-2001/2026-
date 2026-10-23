#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edupub.geo_course import build_course

if __name__ == "__main__":
    for path in build_course():
        print(path)
