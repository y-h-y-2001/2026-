# Aladin ebook capture (macOS)

Screenshot pages from the **official Aladin ebook desktop app on Mac** into **PNG + PDF** for **personal** library use and AI ingestion.

Based on [p0tat0-113/ebookAutoCapture](https://github.com/p0tat0-113/ebookAutoCapture). This package retargets that screenshot loop for **native macOS** (Retina scaling, TCC permissions) and adds a **CLI + YAML config** so Claude / GPT / Cursor can run it end-to-end.

## Viewer

Aladin provides a **native Mac desktop viewer**:

- Mac App Store → **알라딘 eBook** ([App Store](https://apps.apple.com/kr/app/알라딘-ebook/id1023251042), macOS 12+)
- Also linked from [알라딘 전자책 뷰어 다운로드](https://www.aladin.co.kr/events/wevent.aspx?EventId=212360) as **Mac 뷰어**

“PC 이북 앱” here means that **desktop app**, not a Windows VM.

## Scope

| Allowed | Not allowed |
|---------|-------------|
| Automate screenshots of the official Mac viewer for books you purchased | DRM key cracking / license bypass |
| Export page PNGs + a merged PDF for your own notes and local AI tools | Sharing or selling captured books |

## Requirements (Mac)

- **macOS** desktop (Apple Silicon or Intel) with a display session
- Python **3.10+**
- **알라딘 eBook** installed; book opened and readable
- **Screen Recording** permission for Terminal / iTerm / Cursor / Python  
  `System Settings → Privacy & Security → Screen Recording`
- **Accessibility** permission for the same app (page-turn keys via `pyautogui`)  
  `System Settings → Privacy & Security → Accessibility`
- Focus the Aladin window before capture starts (`start_delay_sec` helps)

Cloud/Linux agents can run `doctor`, `validate-config`, `dry-run`, and `pytest`. Real `capture` must run on the user’s Mac.

## Install (Mac)

```bash
cd aladin-ebook-capture
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Quick start (agent or human)

```bash
cp config.example.yaml config.yaml
# Edit book.title, book.pages, capture.region (or calibrate)

python -m aladin_capture doctor
python -m aladin_capture validate-config -c config.yaml
python -m aladin_capture dry-run -c config.yaml

# Calibrate region (logical points; Retina-safe):
python -m aladin_capture calibrate -o region-snippet.yaml
# Merge capture.region into config.yaml

# Focus 알라딘 eBook, then:
python -m aladin_capture capture -c config.yaml

# PDF only from existing PNGs:
python -m aladin_capture export-pdf -c config.yaml
```

Optional GUI:

```bash
python -m aladin_capture.gui
```

## Retina coordinates

| Setting | Meaning |
|---------|---------|
| `coordinate_space: logical` | Region from `calibrate` / `pyautogui` (points). **Default.** |
| `retina_scale: auto` | Detect backing scale (often `2.0` on Retina) at capture time |
| `coordinate_space: physical` | Region already in mss pixel coords (no multiply) |

If crops look half-sized or shifted, set `retina_scale: 2` (or `1` on non-Retina) explicitly.

## Page turning

Default: `next_page: key:right` (typical for Aladin desktop). Also supported: `key:left`, `key:pagedown`, `key:space`, `click`. If turns fail, enable Accessibility and confirm the viewer is focused.

## CLI summary

| Command | Purpose | Needs Mac display? |
|---------|---------|-------------------|
| `doctor` | Scale + Screen Recording probe + permission guide | Probe only on macOS |
| `validate-config -c FILE` | Schema / region sanity check | No |
| `dry-run -c FILE` | JSON plan including physical mss region | No |
| `capture -c FILE` | Screenshot loop + PDF | Yes (macOS) |
| `capture -c FILE --dry-run` | Same as dry-run | No |
| `export-pdf -c FILE` | PNG sequence → PDF | No |
| `calibrate` | Pick region with mouse (logical) | Yes |

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
