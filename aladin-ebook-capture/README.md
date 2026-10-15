# Aladin ebook capture

Screenshot pages from the **official Aladin ebook viewer** into PNG (and optional PDF) for **personal** library use and AI ingestion.

Based on [p0tat0-113/ebookAutoCapture](https://github.com/p0tat0-113/ebookAutoCapture) (Yes24/Aladin-tested Windows screenshot automation). This fork adds a **CLI + YAML config** so Claude / GPT / Cursor can run capture end-to-end without clicking the Tkinter UI.

## Scope

| Allowed | Not allowed |
|---------|-------------|
| Automate screenshots of the official viewer for books you purchased | DRM key cracking / license bypass |
| Export page images / PDF for your own notes and local AI tools | Sharing or selling captured books |

## Requirements

- **Windows 10/11 (Intel)** desktop — matches Aladin PC viewer + upstream testing
- Python **3.10+**
- Aladin PC ebook viewer installed; book opened and readable
- For keyboard page-turn: viewer window **focused**; run terminal **as Administrator** if `pyautogui` fails (upstream note)

Real capture needs a local display. Cloud Linux agents can still `validate-config` / `dry-run` / run unit tests.

## Install

```powershell
cd aladin-ebook-capture
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

## Quick start (agent or human)

```powershell
copy config.example.yaml config.yaml
# Edit book.title, book.pages, capture.region, output.dir

python -m aladin_capture validate-config -c config.yaml
python -m aladin_capture dry-run -c config.yaml

# Focus Aladin viewer, then:
python -m aladin_capture capture -c config.yaml

# Or PDF only from existing PNGs:
python -m aladin_capture export-pdf -c config.yaml
```

Calibrate region interactively:

```powershell
python -m aladin_capture calibrate -o region-snippet.yaml
# Merge the printed capture.region into config.yaml
```

Optional GUI (upstream-style):

```powershell
python -m aladin_capture.gui
```

## CLI summary

| Command | Purpose | Needs display? |
|---------|---------|----------------|
| `validate-config -c FILE` | Schema / region sanity check | No |
| `dry-run -c FILE` | JSON plan of files that would be written | No |
| `capture -c FILE` | Screenshot loop + optional PDF | Yes (Windows) |
| `capture -c FILE --dry-run` | Same as dry-run | No |
| `export-pdf -c FILE` | PNG sequence → PDF | No |
| `calibrate` | Pick region with mouse | Yes |

## Output layout

```
output/
  example-book/
    page-0001.png
    page-0002.png
    ...
    manifest.json
    example-book.pdf
```

## Credits

Capture approach adapted from **p0tat0-113/ebookAutoCapture**. See `AGENTS.md` for the AI-agent runbook.
