"""Indexing helpers for pseudo-widget trees."""

from __future__ import annotations

from .stack import WidgetStack


def flatten_widget_stacks(
    stacks: dict[str, WidgetStack] | list[WidgetStack],
    *,
    allow_duplicates: bool = False,
) -> dict[str, WidgetStack]:
    """
    Return a flat name -> WidgetStack mapping from one or more root stacks.

    Parameters
    ----------
    stacks:
        Root pseudo-widget stacks, either as a dictionary or a list.

    allow_duplicates:
        If False, duplicate widget names raise ValueError.
        If True, the first occurrence is kept.

    Returns
    -------
    dict[str, WidgetStack]
        Flat lookup dictionary keyed by widget name.
    """

    roots = list(stacks.values()) if isinstance(stacks, dict) else list(stacks)

    flat: dict[str, WidgetStack] = {}

    for root in roots:
        for node in root.iter_depth_first():
            if node.name in flat:
                if allow_duplicates:
                    continue

                raise ValueError(
                    f"Duplicate widget name {node.name!r}: "
                    f"{flat[node.name].path!r} and {node.path!r}"
                )

            flat[node.name] = node

    return flat
