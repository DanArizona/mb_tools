# src/mb_tools/windowing.py

"""
Reusable OS-window helpers for GUI automation.

These helpers are intentionally based on stable title prefixes rather than
exact window-title matches. That supports windows whose right side changes,
such as:

    Main@thinkorswim [build 1991]
    Main@thinkorswim [build 1992]
"""

from __future__ import annotations

from dataclasses import replace
import logging
from typing import Any, Optional

import pygetwindow as gw


def find_window_by_title_prefix(title_prefix: str) -> Optional[Any]:
    """
    Find an OS window whose title starts with title_prefix.

    Returns a pygetwindow Window object, or None if no match is found.
    """
    prefix = title_prefix.strip().lower()

    if not prefix:
        return None

    all_windows = [
        w
        for w in gw.getAllWindows()
        if w.title and w.title.strip() and w.width > 0 and w.height > 0
    ]

    matches = [
        w
        for w in all_windows
        if w.title.strip().lower().startswith(prefix)
    ]

    if not matches:
        return None

    visible_matches = [
        w
        for w in matches
        if getattr(w, "isVisible", True)
    ]

    if visible_matches:
        return visible_matches[0]

    return matches[0]


def is_window_visible_by_prefix(title_prefix: str) -> bool:
    """
    Return True if a window matching title_prefix exists.
    """
    return find_window_by_title_prefix(title_prefix) is not None


def bring_window_to_front_by_prefix(
    title_prefix: str,
    logger: logging.Logger | None = None,
) -> bool:
    """
    Bring the first window matching title_prefix to the front.

    Returns True if a matching window was found and activation was attempted
    successfully. Returns False otherwise.
    """
    window = find_window_by_title_prefix(title_prefix)

    if window is None:
        if logger:
            logger.warning(
                "Could not bring window to front. No match for prefix %r.",
                title_prefix,
            )
        return False

    try:
        if getattr(window, "isMinimized", False):
            window.restore()

        window.activate()

        if logger:
            logger.info(
                "Brought window to front: prefix=%r matched=%r",
                title_prefix,
                window.title,
            )

        return True

    except Exception:
        if logger:
            logger.exception(
                "Failed to bring window to front: prefix=%r matched=%r",
                title_prefix,
                window.title,
            )
        return False


def get_root_title_prefix(
    widget_name: str,
    widget_stacks: dict[str, Any],
    title_map: dict[str, str],
) -> str:
    """
    Resolve a widget name to its root window title prefix.

    widget_stacks values are expected to support .root().name.
    """
    root_name = widget_stacks[widget_name].root().name
    return title_map[root_name]


def is_widget_window_visible(
    widget_name: str,
    widget_stacks: dict[str, Any],
    title_map: dict[str, str],
) -> bool:
    """
    Return True if the OS window owning widget_name is visible/found.
    """
    title_prefix = get_root_title_prefix(widget_name, widget_stacks, title_map)
    return is_window_visible_by_prefix(title_prefix)


def bring_widget_window_to_front(
    widget_name: str,
    widget_stacks: dict[str, Any],
    title_map: dict[str, str],
    logger: logging.Logger | None = None,
) -> bool:
    """
    Bring the OS window owning widget_name to the front.
    """
    title_prefix = get_root_title_prefix(widget_name, widget_stacks, title_map)
    return bring_window_to_front_by_prefix(title_prefix, logger=logger)


def update_root_window_positions(
    widget_stacks: dict[str, Any],
    title_map: dict[str, str],
    logger: logging.Logger | None = None,
    *,
    size_tolerance: int = 4,
) -> None:
    """
    Update top-level pseudo-widget X/Y positions from current OS window positions.

    title_map values are stable window-title prefixes.

    YAML width/height are left unchanged.
    Only root widget X/Y values are updated.

    If the OS window size differs significantly from the YAML size,
    log a warning.

    widget_stacks values are expected to have:
        .region
        .region.x_tl
        .region.y_tl
        .region.width
        .region.height

    The region object may be frozen; this function uses dataclasses.replace().
    """
    for root_name, title_prefix in title_map.items():
        root_widget = widget_stacks.get(root_name)

        if root_widget is None:
            if logger:
                logger.warning(
                    "Root widget %r from title_map was not found in widget_stacks.",
                    root_name,
                )
            continue

        window = find_window_by_title_prefix(title_prefix)

        if window is None:
            if logger:
                logger.warning(
                    "Could not find OS window for root widget %r using title prefix %r.",
                    root_name,
                    title_prefix,
                )
            continue

        yaml_width = root_widget.region.width
        yaml_height = root_widget.region.height
        os_width = window.width
        os_height = window.height

        width_diff = os_width - yaml_width
        height_diff = os_height - yaml_height

        if abs(width_diff) > size_tolerance or abs(height_diff) > size_tolerance:
            if logger:
                logger.warning(
                    "Window size differs from YAML for root %r matched by prefix %r. "
                    "YAML size=(%s, %s), OS size=(%s, %s), diff=(%+d, %+d). "
                    "Child widget positions may be inaccurate.",
                    root_name,
                    title_prefix,
                    yaml_width,
                    yaml_height,
                    os_width,
                    os_height,
                    width_diff,
                    height_diff,
                )

        old_x = root_widget.region.x_tl
        old_y = root_widget.region.y_tl

        root_widget.region = replace(
            root_widget.region,
            x_tl=window.left,
            y_tl=window.top,
        )

        if logger:
            logger.info(
                "Updated root %s from OS window title prefix %r: "
                "matched title=%r, old=(%s, %s), new=(%s, %s), "
                "yaml_size=(%s, %s), os_size=(%s, %s)",
                root_name,
                title_prefix,
                window.title,
                old_x,
                old_y,
                root_widget.region.x_tl,
                root_widget.region.y_tl,
                yaml_width,
                yaml_height,
                os_width,
                os_height,
            )
