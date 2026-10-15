"""macOS helpers: Retina scale, permission doctor, region → mss pixels.

Aladin ships a native desktop viewer for Mac (App Store: "알라딘 eBook",
macOS 12+). Capture still needs Screen Recording + Accessibility so this
process can screenshot and send page-turn keys.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from typing import Any

from .config import Region


def is_macos() -> bool:
    return sys.platform == "darwin"


@dataclass(frozen=True)
class DisplayScale:
    """Logical (point) vs physical (pixel) relationship for the main display."""

    logical_width: int
    logical_height: int
    physical_width: int
    physical_height: int
    scale: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "logical_width": self.logical_width,
            "logical_height": self.logical_height,
            "physical_width": self.physical_width,
            "physical_height": self.physical_height,
            "scale": self.scale,
            "source": self.source,
        }


def detect_display_scale() -> DisplayScale:
    """Best-effort Retina scale. Works without display on non-mac (returns 1.0)."""
    if not is_macos():
        return DisplayScale(0, 0, 0, 0, 1.0, "non-macos-default")

    # Prefer AppKit backingScaleFactor when available (PyObjC / system Python).
    try:
        from AppKit import NSScreen  # type: ignore[import-not-found]

        screen = NSScreen.mainScreen()
        if screen is not None:
            frame = screen.frame()
            scale = float(screen.backingScaleFactor())
            lw = int(frame.size.width)
            lh = int(frame.size.height)
            return DisplayScale(
                logical_width=lw,
                logical_height=lh,
                physical_width=int(lw * scale),
                physical_height=int(lh * scale),
                scale=scale,
                source="appkit",
            )
    except Exception:  # noqa: BLE001 — optional dependency / headless
        pass

    # Fallback: compare mss physical monitor size to pyautogui logical size.
    try:
        import mss
        import pyautogui

        with mss.mss() as sct:
            # monitors[1] is the first real display (0 is virtual all-in-one)
            mon = sct.monitors[1]
            pw, ph = int(mon["width"]), int(mon["height"])
        lw, lh = pyautogui.size()
        if lw > 0 and lh > 0:
            scale = pw / float(lw)
            return DisplayScale(lw, lh, pw, ph, scale, "mss-vs-pyautogui")
    except Exception:  # noqa: BLE001
        pass

    return DisplayScale(0, 0, 0, 0, 2.0, "macos-retina-fallback")


def resolve_scale(configured: float | None) -> DisplayScale:
    """If configured is set, wrap it; else detect."""
    if configured is not None:
        detected = detect_display_scale()
        return DisplayScale(
            logical_width=detected.logical_width,
            logical_height=detected.logical_height,
            physical_width=detected.physical_width,
            physical_height=detected.physical_height,
            scale=float(configured),
            source=f"config:{configured}",
        )
    return detect_display_scale()


def region_to_mss(
    region: Region,
    *,
    coordinate_space: str,
    scale: float,
) -> dict[str, int]:
    """Convert config region to an mss grab dict in physical pixels.

    - logical: coords from pyautogui / calibrate (points) → multiply by scale
    - physical: already mss pixel coords → use as-is
    """
    if coordinate_space == "physical":
        return region.as_mss_monitor()
    if coordinate_space != "logical":
        raise ValueError(f"Unknown coordinate_space: {coordinate_space}")

    s = float(scale)
    if s <= 0:
        raise ValueError(f"scale must be > 0, got {s}")
    left = int(round(region.left * s))
    top = int(round(region.top * s))
    width = int(round(region.width * s))
    height = int(round(region.height * s))
    return {"left": left, "top": top, "width": width, "height": height}


PERMISSION_GUIDE = {
    "screen_recording": (
        "System Settings → Privacy & Security → Screen Recording → enable your "
        "Terminal / iTerm / Cursor / Python. Quit and reopen the app after changing."
    ),
    "accessibility": (
        "System Settings → Privacy & Security → Accessibility → enable the same "
        "app so page-turn keys (pyautogui) can be sent to 알라딘 eBook."
    ),
}


def probe_screen_recording() -> dict[str, Any]:
    """Try a 1×1 grab. On macOS, failure usually means Screen Recording is off."""
    if not is_macos():
        return {
            "status": "skipped",
            "detail": f"host is {platform.system()}, not macOS",
        }
    try:
        import mss

        with mss.mss() as sct:
            sct.grab({"left": 0, "top": 0, "width": 1, "height": 1})
        return {"status": "ok", "detail": "mss 1x1 grab succeeded"}
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "fail",
            "detail": str(exc),
            "fix": PERMISSION_GUIDE["screen_recording"],
        }


def doctor_report() -> dict[str, Any]:
    """JSON-serializable preflight for agents on the user's Mac."""
    scale = detect_display_scale()
    screen = probe_screen_recording()
    return {
        "target_os": "macOS",
        "host_platform": sys.platform,
        "host_system": platform.system(),
        "is_macos": is_macos(),
        "aladin_viewer": {
            "name": "알라딘 eBook",
            "install": "Mac App Store → search '알라딘 eBook' (macOS 12+)",
            "also": "https://www.aladin.co.kr/events/wevent.aspx?EventId=212360 (Mac 뷰어)",
            "note": (
                "Native macOS desktop viewer exists (not a Windows VM). "
                "Focus that app window before capture."
            ),
        },
        "display_scale": scale.to_dict(),
        "permissions": {
            "screen_recording": screen,
            "accessibility": {
                "status": "manual",
                "fix": PERMISSION_GUIDE["accessibility"],
                "detail": (
                    "Cannot fully probe Accessibility without sending a keystroke; "
                    "enable it before capture if page turns do nothing."
                ),
            },
        },
        "ready_for_capture": bool(is_macos() and screen.get("status") == "ok"),
        "blocker_if_not_macos": (
            None
            if is_macos()
            else "Real capture must run on the user's Mac desktop with 알라딘 eBook open."
        ),
    }
