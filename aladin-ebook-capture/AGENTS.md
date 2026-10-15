# AGENTS.md — macOS runbook for Claude / GPT / Cursor

You are setting up or running **personal** Aladin ebook page capture on the user’s **Mac**. Use only for ebooks the user purchased. Prefer official-viewer screenshots. **Never** implement DRM decrypt, license bypass, or piracy distribution.

## Target

| Item | Value |
|------|--------|
| OS | **macOS** (native desktop, not Windows VM) |
| Viewer | **알라딘 eBook** Mac App Store app (macOS 12+) |
| Output | **PNG pages + merged PDF** |
| Repo path | `aladin-ebook-capture/` |

If you are in a **headless/cloud/Linux** environment: only run `doctor`, `validate-config`, `dry-run`, and `pytest`. Do **not** claim capture succeeded without a Mac desktop.

## Mac permissions (user must grant once)

1. **Screen Recording** — Terminal / iTerm / Cursor / Python  
   `System Settings → Privacy & Security → Screen Recording`  
   Quit and reopen the app after enabling.
2. **Accessibility** — same app, for `pyautogui` page turns  
   `System Settings → Privacy & Security → Accessibility`

## Setup (idempotent, Mac)

```bash
cd aladin-ebook-capture
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Cloud / any-OS smoke (no capture):

```bash
cd aladin-ebook-capture
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
pytest -q
python -m aladin_capture doctor
python -m aladin_capture validate-config -c config.example.yaml
python -m aladin_capture dry-run -c config.example.yaml
```

## Exact Mac capture sequence

```bash
cd aladin-ebook-capture
source .venv/bin/activate

python -m aladin_capture doctor
# Fix Screen Recording / Accessibility if doctor reports fail

cp -n config.example.yaml config.yaml
# Open 알라딘 eBook, open purchased book, arrange page area

python -m aladin_capture calibrate -o region-snippet.yaml
# Merge printed capture.region (+ keep coordinate_space: logical, retina_scale: auto)

# Edit config.yaml: book.title, book.pages, delay_ms if needed
python -m aladin_capture validate-config -c config.yaml
python -m aladin_capture dry-run -c config.yaml

# Focus 알라딘 eBook window, then:
python -m aladin_capture capture -c config.yaml
# Produces output/<title>/page-*.png, manifest.json, and <title>.pdf
```

## Config contract

- Required: `book.title`, `book.pages`, `capture.region.{left,top,right,bottom}`
- Defaults: `coordinate_space: logical`, `retina_scale: auto`, `next_page: key:right`, `delay_ms: 500`
- Output: `images: true` and `pdf: true` (both)
- Retina: logical points from calibrate are scaled for `mss` physical pixels

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Black / empty screenshots | Enable Screen Recording; relaunch Terminal/Cursor |
| Pages do not advance | Enable Accessibility; focus Aladin; try `key:space` or `click` |
| Crop half-size / wrong offset | Set `retina_scale: 2` (or `1`); re-run calibrate |
| `RuntimeError: ... not macOS` | Run `capture` on the user’s Mac, not in cloud |

## Do / don’t

- **Do** use mss region screenshots + keyboard/click page turns against 알라딘 eBook.
- **Do** keep personal-use messaging in logs / `manifest.json`.
- **Don’t** add DRM key extractors or decrypt tools.
- **Don’t** skip `doctor` on a fresh Mac.

## Tests after code changes

```bash
pytest -q
python -m aladin_capture doctor
python -m aladin_capture validate-config -c config.example.yaml
```

## Upstream

Logic adapted from https://github.com/p0tat0-113/ebookAutoCapture — credit that project when changing capture behavior.
