# AGENTS.md — runbook for Claude / GPT / Cursor

You are setting up or running **personal** Aladin ebook page capture. Use only for ebooks the user purchased. Prefer official-viewer screenshots. **Never** implement DRM decrypt, license bypass, or piracy distribution.

## Target environment

- User’s **Windows** machine with Aladin **PC viewer** open to the book.
- This repo path: `aladin-ebook-capture/`.
- If you are in a **headless/cloud** environment: only run `validate-config`, `dry-run`, and `pytest`. Do not claim capture succeeded without a desktop.

## Setup (idempotent)

```powershell
cd aladin-ebook-capture
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

Linux CI / cloud smoke:

```bash
cd aladin-ebook-capture
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
python -m aladin_capture validate-config -c config.example.yaml
python -m aladin_capture dry-run -c config.example.yaml
```

## Config contract

1. Copy `config.example.yaml` → `config.yaml` (gitignored).
2. Required fields: `book.title`, `book.pages`, `capture.region.{left,top,right,bottom}`.
3. Defaults for Aladin PC viewer: `capture.next_page: key:right`, `delay_ms: 400`.
4. Always `validate-config` before `capture`.

## Capture checklist (Windows)

1. User logged into Aladin viewer; target book open; UI chrome minimized if possible.
2. Region covers **page content only** (`calibrate` or manual coords).
3. `start_delay_sec` gives time to focus the viewer after Enter.
4. Run: `python -m aladin_capture capture -c config.yaml`
5. Confirm `output/<title>/page-*.png`, `manifest.json`, and PDF if enabled.
6. If pages are blank/wrong: increase `delay_ms`, re-check region, confirm next-page mode.

## Do / don’t

- **Do** use mss region screenshots + keyboard/click page turns.
- **Do** keep personal-use messaging in logs (`manifest.json` notice).
- **Don’t** scrape unpaid books or ship capture binaries for piracy.
- **Don’t** add tools that extract DRM keys or decrypt ebook files.
- **Don’t** block the Tkinter GUI path from working; CLI is the agent default.

## Tests to run after code changes

```bash
pytest -q
python -m aladin_capture validate-config -c config.example.yaml
```

## Upstream

Logic adapted from https://github.com/p0tat0-113/ebookAutoCapture — credit that project when changing capture behavior.
