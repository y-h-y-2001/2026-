"""Command-line interface for AI agents and humans (macOS target)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .capture import PERSONAL_USE, dry_run_plan, run_capture
from .config import ConfigError, load_config
from .export_pdf import export_pdf
from .macos import doctor_report, is_macos, resolve_scale


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aladin_capture",
        description=(
            "Screenshot pages from the official Aladin ebook desktop app on macOS "
            "for personal use. Does not decrypt or bypass DRM."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "doctor",
        help="macOS preflight: Retina scale + Screen Recording probe + permission guide",
    )

    p_val = sub.add_parser("validate-config", help="Load and validate a YAML config")
    p_val.add_argument("-c", "--config", type=Path, required=True)

    p_dry = sub.add_parser("dry-run", help="Print capture plan without screenshots")
    p_dry.add_argument("-c", "--config", type=Path, required=True)

    p_cap = sub.add_parser(
        "capture",
        help="Run page capture (macOS; focus 알라딘 eBook first)",
    )
    p_cap.add_argument("-c", "--config", type=Path, required=True)
    p_cap.add_argument(
        "--dry-run",
        action="store_true",
        help="Same as dry-run subcommand (no screen access)",
    )
    p_cap.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Do not build PDF even if config.output.pdf is true",
    )

    p_pdf = sub.add_parser("export-pdf", help="Build PDF from existing page PNGs")
    p_pdf.add_argument("-c", "--config", type=Path, required=True)
    p_pdf.add_argument(
        "--book-dir",
        type=Path,
        default=None,
        help="Override directory containing page-*.png",
    )

    p_cal = sub.add_parser(
        "calibrate",
        help="Interactive region picker (macOS; logical points for Retina)",
    )
    p_cal.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("region-snippet.yaml"),
        help="Where to write the region YAML snippet",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "doctor":
            report = doctor_report()
            print(json.dumps(report, indent=2, ensure_ascii=False))
            if not report["is_macos"]:
                return 0  # informative on CI; not a hard failure
            if report["permissions"]["screen_recording"].get("status") == "fail":
                return 3
            return 0

        if args.command == "validate-config":
            cfg = load_config(args.config)
            scale = resolve_scale(cfg.retina_scale)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "target_os": "macOS",
                        "title": cfg.title,
                        "pages": cfg.pages,
                        "book_dir": str(cfg.book_dir),
                        "region": {
                            "left": cfg.region.left,
                            "top": cfg.region.top,
                            "right": cfg.region.right,
                            "bottom": cfg.region.bottom,
                            "width": cfg.region.width,
                            "height": cfg.region.height,
                        },
                        "coordinate_space": cfg.coordinate_space,
                        "retina_scale": scale.to_dict(),
                        "next_page": cfg.next_page,
                        "output_images": cfg.save_images,
                        "output_pdf": cfg.save_pdf,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0

        if args.command == "dry-run":
            cfg = load_config(args.config)
            print(json.dumps(dry_run_plan(cfg), indent=2, ensure_ascii=False))
            return 0

        if args.command == "capture":
            cfg = load_config(args.config)
            book_dir = run_capture(cfg, dry_run=bool(args.dry_run))
            if not args.dry_run and cfg.save_pdf and not args.skip_pdf:
                export_pdf(cfg, book_dir)
            print(str(book_dir.resolve()))
            return 0

        if args.command == "export-pdf":
            cfg = load_config(args.config)
            out = export_pdf(cfg, args.book_dir)
            print(str(out.resolve()))
            return 0

        if args.command == "calibrate":
            return _calibrate(args.output)

    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"Not found: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Aborted.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _calibrate(output: Path) -> int:
    print(PERSONAL_USE, file=sys.stderr)
    if not is_macos():
        print(
            "Warning: calibrate is intended for macOS. Continuing anyway for coords only.",
            file=sys.stderr,
        )
    print(
        "Coords are logical points (pyautogui). On Retina, capture scales them for mss.\n"
        "Move the mouse to the TOP-LEFT of the page area, then press Enter.",
        file=sys.stderr,
    )
    try:
        import pyautogui
    except ImportError as exc:
        print(f"pyautogui required for calibrate: {exc}", file=sys.stderr)
        return 1

    input()
    x1, y1 = pyautogui.position()
    print(f"Top-left (logical): ({x1}, {y1})", file=sys.stderr)
    print(
        "Move the mouse to the BOTTOM-RIGHT of the page area, then press Enter.",
        file=sys.stderr,
    )
    input()
    x2, y2 = pyautogui.position()
    print(f"Bottom-right (logical): ({x2}, {y2})", file=sys.stderr)

    scale = resolve_scale(None)
    snippet = (
        "capture:\n"
        "  # logical = pyautogui / calibrate points; mss uses physical pixels via retina_scale\n"
        "  coordinate_space: logical\n"
        "  retina_scale: auto\n"
        "  region:\n"
        f"    left: {min(x1, x2)}\n"
        f"    top: {min(y1, y2)}\n"
        f"    right: {max(x1, x2)}\n"
        f"    bottom: {max(y1, y2)}\n"
    )
    output.write_text(snippet, encoding="utf-8")
    print(snippet)
    print(
        f"Detected scale≈{scale.scale} ({scale.source}). Wrote {output.resolve()}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
