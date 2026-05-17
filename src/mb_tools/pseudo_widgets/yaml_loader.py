"""
YAML loader for pseudo-widget layouts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .region import WidgetRegion
from .stack import WidgetStack


class WidgetYamlError(ValueError):
    """Raised when pseudo-widget YAML cannot be loaded."""


def load_widget_stacks(path: str | Path) -> dict[str, WidgetStack]:
    """
    Load root widget stacks from a YAML file.

    Returns
    -------
    dict[str, WidgetStack]
        Mapping of root-name to root WidgetStack.
    """
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        return {}

    if not isinstance(raw, dict):
        raise WidgetYamlError("Top-level YAML structure must be a mapping.")

    roots: dict[str, WidgetStack] = {}

    for name, node_data in raw.items():
        roots[str(name)] = _node_from_mapping(
            name=str(name),
            data=node_data,
            parent=None,
        )

    return roots


def _node_from_mapping(
    *,
    name: str,
    data: Any,
    parent: WidgetStack | None,
) -> WidgetStack:
    if not isinstance(data, dict):
        raise WidgetYamlError(f"Widget {name!r} must be a mapping.")

    try:
        width = int(data["width"])
        height = int(data["height"])
        x_tl = int(data["Xtl"])
        y_tl = int(data["Ytl"])
    except KeyError as exc:
        raise WidgetYamlError(
            f"Widget {name!r} is missing required field {exc.args[0]!r}."
        ) from exc
    except (TypeError, ValueError) as exc:
        raise WidgetYamlError(
            f"Widget {name!r} has non-integer geometry."
        ) from exc

    ptxt = data.get("ptxt", "")
    coord = data.get("coord", "parent")

    if ptxt is None:
        ptxt = ""

    node = WidgetStack(
        name=name,
        region=WidgetRegion(
            width=width,
            height=height,
            x_tl=x_tl,
            y_tl=y_tl,
        ),
        ptxt=str(ptxt),
        coord=str(coord),
        parent=parent,
    )

    children_data = data.get("children", {})

    if children_data is None:
        children_data = {}

    if not isinstance(children_data, dict):
        raise WidgetYamlError(
            f"Widget {name!r} has children field that is not a mapping."
        )

    for child_name, child_data in children_data.items():
        child = _node_from_mapping(
            name=str(child_name),
            data=child_data,
            parent=node,
        )
        node.add_child(child)

    return node
