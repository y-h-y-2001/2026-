#!/bin/bash
# 이 파일을 더블클릭하면 터미널이 열리고 메뉴가 나옵니다.
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "이 컴퓨터에서 python3를 찾지 못했습니다."
  echo "https://www.python.org/downloads/ 에서 Python 3를 설치한 뒤 다시 열어 주세요."
  read -r -p "엔터를 누르면 창을 닫습니다. "
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "처음 실행입니다. 이 폴더 안에만 파이썬 환경을 만듭니다."
  if ! python3 -m venv .venv; then
    echo "가상환경을 만들지 못했습니다. python.org에서 설치한 Python 3로 다시 시도해 주세요."
    read -r -p "엔터를 누르면 창을 닫습니다. "
    exit 1
  fi
fi

# shellcheck disable=SC1091
source ".venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python "프로그램/메뉴.py"
echo
read -r -p "엔터를 누르면 창을 닫습니다. "
