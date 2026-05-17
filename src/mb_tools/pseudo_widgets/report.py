"""
Text reporting helpers for pseudo-widget trees.
"""

from __future__ import annotations

from .stack import WidgetStack


def format_widget_tree(
    stacks: dict[str, WidgetStack] | list[WidgetStack],
    *,
    show_abs: bool = True,
    show_text: bool = True,
) -> str:
    """
    Return a printable tree report.
    """
    roots = list(stacks.values()) if isinstance(stacks, dict) else list(stacks)

    lines: list[str] = []

    for index, root in enumerate(roots):
        if index > 0:
            lines.append("")

        _format_node(
            root,
            lines=lines,
            prefix="",
            is_last=True,
            show_abs=show_abs,
            show_text=show_text,
        )

    return "\n".join(lines)


def print_widget_tree(
    stacks: dict[str, WidgetStack] | list[WidgetStack],
    *,
    show_abs: bool = True,
    show_text: bool = True,
) -> None:
    """
    Print a pseudo-widget tree report.
    """
    print(
        format_widget_tree(
            stacks,
            show_abs=show_abs,
            show_text=show_text,
        )
    )


def _format_node(
    node: WidgetStack,
    *,
    lines: list[str],
    prefix: str,
    is_last: bool,
    show_abs: bool,
    show_text: bool,
) -> None:
    connector = "└─ " if is_last else "├─ "
    branch = "" if node.parent is None else prefix + connector

    rel = node.region.as_tuple()
    parts = [
        f"{branch}{node.name}",
        f"rel={rel}",
        f"coord={node.coord!r}",
    ]

    if show_abs:
        parts.append(f"abs={node.absolute_region().as_tuple()}")
        parts.append(f"center={node.absolute_center()}")

    if show_text and node.ptxt:
        parts.append(f"text={node.ptxt!r}")

    lines.append("  ".join(parts))

    child_prefix = prefix

    if node.parent is not None:
        child_prefix += "   " if is_last else "│  "

    for idx, child in enumerate(node.children):
        _format_node(
            child,
            lines=lines,
            prefix=child_prefix,
            is_last=idx == len(node.children) - 1,
            show_abs=show_abs,
            show_text=show_text,
        )
