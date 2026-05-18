from __future__ import annotations

import argparse
import sys


def survey_windows(*, visible_only: bool = True) -> list[dict[str, object]]:
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

        records.append(
            {
                "title": title,
                "left": win.left,
                "top": win.top,
                "width": win.width,
                "height": win.height,
                "right": win.left + win.width,
                "bottom": win.top + win.height,
            }
        )

    records.sort(
        key=lambda r: (
            str(r["title"]).lower(),
            int(r["top"]),
            int(r["left"]),
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
        f"{'#':>3}  "
        f"{'Left':>6}  "
        f"{'Top':>6}  "
        f"{'Width':>6}  "
        f"{'Height':>6}  "
        f"Title"
    )
    print("-" * 100)

    for i, rec in enumerate(records, start=1):
        print(
            f"{i:>3}  "
            f"{rec['left']:>6}  "
            f"{rec['top']:>6}  "
            f"{rec['width']:>6}  "
            f"{rec['height']:>6}  "
            f"{rec['title']}"
        )


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

    args = parser.parse_args()

    try:
        records = survey_windows(visible_only=not args.all)
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
