from __future__ import annotations

import argparse
import sys
import ctypes
from ctypes import wintypes
from collections.abc import Mapping


def _field_as_int(record: Mapping[str, object], key: str) -> int:
    value = record[key]

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        return int(value)

    raise TypeError(f"Expected int-compatible field {key!r}, got {type(value).__name__}")


def _field_as_str(record: Mapping[str, object], key: str) -> str:
    return str(record[key])


def _field_as_optional_int(record: Mapping[str, object], key: str) -> int | None:
    value = record.get(key)

    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        if not value:
            return None

        return int(value)

    raise TypeError(f"Expected int-compatible field {key!r}, got {type(value).__name__}")


def _z_order_sort_value(record: Mapping[str, object]) -> int:
    z_order = _field_as_optional_int(record, "z_order")
    return z_order if z_order is not None else 999999


def _get_hwnd_from_pygetwindow(win: object) -> int | None:
    """
    Return the native Windows HWND from a pygetwindow window object, if available.

    pygetwindow's Windows backend exposes this as _hWnd.
    Keeping this access in one helper makes the private-attribute usage easy
    to replace later if needed.
    """
    hwnd = getattr(win, "_hWnd", None)

    if isinstance(hwnd, int) and hwnd:
        return hwnd

    return None


def _build_z_order_map(max_windows: int = 1000) -> dict[int, int]:
    """
    Return {hwnd: z_order}, where z_order=0 is frontmost.

    Windows only. On non-Windows platforms, return an empty mapping.
    """
    if sys.platform != "win32":
        return {}

    user32 = ctypes.windll.user32

    GetTopWindow = user32.GetTopWindow
    GetTopWindow.argtypes = [wintypes.HWND]
    GetTopWindow.restype = wintypes.HWND

    GetWindow = user32.GetWindow
    GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    GetWindow.restype = wintypes.HWND

    IsWindow = user32.IsWindow
    IsWindow.argtypes = [wintypes.HWND]
    IsWindow.restype = wintypes.BOOL

    GW_HWNDNEXT = 2

    z_order: dict[int, int] = {}

    hwnd = GetTopWindow(None)
    index = 0

    while hwnd and index < max_windows:
        if IsWindow(hwnd):
            z_order[int(hwnd)] = index
            index += 1

        hwnd = GetWindow(hwnd, GW_HWNDNEXT)

    return z_order


def _get_foreground_hwnd() -> int | None:
    if sys.platform != "win32":
        return None

    user32 = ctypes.windll.user32

    GetForegroundWindow = user32.GetForegroundWindow
    GetForegroundWindow.argtypes = []
    GetForegroundWindow.restype = wintypes.HWND

    hwnd = GetForegroundWindow()
    return int(hwnd) if hwnd else None


def _is_topmost_hwnd(hwnd: int | None) -> bool:
    if sys.platform != "win32" or not hwnd:
        return False

    user32 = ctypes.windll.user32

    GetWindowLongW = user32.GetWindowLongW
    GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    GetWindowLongW.restype = ctypes.c_long

    GWL_EXSTYLE = -20
    WS_EX_TOPMOST = 0x00000008

    ex_style = GetWindowLongW(hwnd, GWL_EXSTYLE)
    return bool(ex_style & WS_EX_TOPMOST)


def _rects_overlap(a: Mapping[str, object], b: Mapping[str, object]) -> bool:
    ax1 = _field_as_int(a, "left")
    ay1 = _field_as_int(a, "top")
    ax2 = _field_as_int(a, "right")
    ay2 = _field_as_int(a, "bottom")

    bx1 = _field_as_int(b, "left")
    by1 = _field_as_int(b, "top")
    bx2 = _field_as_int(b, "right")
    by2 = _field_as_int(b, "bottom")

    return not (
        ax2 <= bx1 or
        bx2 <= ax1 or
        ay2 <= by1 or
        by2 <= ay1
    )


def _annotate_covered_by(records: list[dict[str, object]]) -> None:
    """
    Add covered_by and covered_by_count to each record.

    A window is considered covered by another surveyed window if that other
    window has a smaller z_order value and overlapping rectangles.

    Assumption:
        z_order=0 is frontmost, and larger z_order values are farther back.
    """
    for rec in records:
        rec_z = rec.get("z_order")

        if not isinstance(rec_z, int):
            rec["covered_by_count"] = 0
            rec["covered_by"] = ""
            continue

        covering_titles: list[str] = []

        for other in records:
            other_z = other.get("z_order")

            if not isinstance(other_z, int):
                continue

            # Only windows in front of this one can cover it.
            if other_z >= rec_z:
                continue

            if _rects_overlap(rec, other):
                covering_titles.append(
                    f"Z={other_z} {other['title']}"
                )

        rec["covered_by_count"] = len(covering_titles)
        rec["covered_by"] = "; ".join(covering_titles)
        
def survey_windows(
    *,
    visible_only: bool = True,
    sort_by_z_order: bool = False,
) -> list[dict[str, object]]:
    """
    Return basic information about open OS windows.

    Parameters
    ----------
    visible_only:
        If True, skip minimized/hidden/zero-size windows when possible.

    Returns
    -------
    list[dict[str, object]]
        Window records containing title, position, and size.
    """
    try:
        import pygetwindow as gw
    except ImportError as exc:
        raise RuntimeError(
            "pygetwindow is required for window_survey. "
            "Please install it in the active environment."
        ) from exc

    z_order_map = _build_z_order_map()
    foreground_hwnd = _get_foreground_hwnd()
    records: list[dict[str, object]] = []

    for win in gw.getAllWindows():
        title = win.title or ""

        if not title.strip():
            continue

        if visible_only:
            if getattr(win, "isMinimized", False):
                continue
            if win.width <= 0 or win.height <= 0:
                continue

        hwnd = _get_hwnd_from_pygetwindow(win)

        z_order: int | None = None
        if hwnd is not None:
            z_order = z_order_map.get(hwnd)

        records.append(
            {
                "title": title,
                "hwnd": f"0x{hwnd:08X}" if hwnd else "",
                "z_order": z_order,
                "is_foreground": hwnd == foreground_hwnd if hwnd else False,
                "is_topmost": _is_topmost_hwnd(hwnd),
                "left": win.left,
                "top": win.top,
                "width": win.width,
                "height": win.height,
                "right": win.left + win.width,
                "bottom": win.top + win.height,
                "covered_by_count": 0,
                "covered_by": "",
            }
        )

    _annotate_covered_by(records)
    if sort_by_z_order:
        records.sort(
            key=lambda r: (
                _z_order_sort_value(r),
                _field_as_str(r, "title").lower(),
            )
        )
    else:
        records.sort(
            key=lambda r: (
                _field_as_str(r, "title").lower(),
                _field_as_int(r, "top"),
                _field_as_int(r, "left"),
            )
        )
        
    return records


def print_window_table(records: list[dict[str, object]]) -> None:
    """
    Print a simple table of surveyed windows.
    """
    if not records:
        print("No matching windows found.")
        return

    print(
        f"{'#':>3} "
        f"{'Z':>4} "
        f"{'FG':>2} "
        f"{'TOP':>3} "
        f"{'COV':>3} "
        f"{'Left':>6} "
        f"{'Top':>6} "
        f"{'Width':>6} "
        f"{'Height':>6} "
        f"{'HWND':>10} "
        f"Title"
    )
    print("-" * 140)

    for i, rec in enumerate(records, start=1):
        print(
            f"{i:>3} "
            f"{str(rec.get('z_order', '')):>4} "
            f"{'Y' if rec.get('is_foreground') else '-':>2} "
            f"{'Y' if rec.get('is_topmost') else '-':>3} "
            f"{rec.get('covered_by_count', 0):>3} "
            f"{rec['left']:>6} "
            f"{rec['top']:>6} "
            f"{rec['width']:>6} "
            f"{rec['height']:>6} "
            f"{rec.get('hwnd', ''):>10} "
            f"{rec['title']}"
        )

        covered_by = str(rec.get("covered_by", "")).strip()
        if covered_by:
            print(f"{'':>3} {'':>4} {'':>2} {'':>3} {'covered by:':>25} {covered_by}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Survey open windows and print title, position, and size."
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Include minimized or zero-size windows when reported by the OS.",
    )

    parser.add_argument(
        "--contains",
        metavar="TEXT",
        help="Only show windows whose title contains this text, case-insensitive.",
    )

    parser.add_argument(
        "--z-order",
        action="store_true",
        help="Sort windows front-to-back by Z-order instead of by title.",
    )

    args = parser.parse_args()

    try:
        records = survey_windows(
            visible_only=not args.all,
            sort_by_z_order=args.z_order,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

    if args.contains:
        needle = args.contains.lower()
        records = [
            rec
            for rec in records
            if needle in str(rec["title"]).lower()
        ]

    print_window_table(records)


if __name__ == "__main__":
    main()
