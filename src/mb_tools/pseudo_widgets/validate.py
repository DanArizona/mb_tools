"""
Validation helpers for pseudo-widget trees.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .stack import WidgetStack


@dataclass(frozen=True)
class ValidationWarning:
    """Non-fatal pseudo-widget validation warning."""

    widget_path: str
    message: str

    def __str__(self) -> str:
        return f"{self.widget_path}: {self.message}"


def validate_stacks(
    stacks: dict[str, WidgetStack] | list[WidgetStack],
) -> list[ValidationWarning]:
    """
    Validate one or more pseudo-widget root stacks.

    The validator is intentionally conservative. Most geometry issues are
    warnings rather than errors because popup menus and external windows can
    legitimately violate parent containment.
    """
    roots = _normalize_roots(stacks)

    warnings: list[ValidationWarning] = []

    warnings.extend(_warn_bad_dimensions(roots))
    warnings.extend(_warn_duplicate_names(roots))
    warnings.extend(_warn_duplicate_sibling_geometry(roots))
    warnings.extend(_warn_parent_containment(roots))

    return warnings


def _normalize_roots(
    stacks: dict[str, WidgetStack] | list[WidgetStack],
) -> list[WidgetStack]:
    if isinstance(stacks, dict):
        return list(stacks.values())

    return list(stacks)


def _iter_all_nodes(roots: list[WidgetStack]) -> list[WidgetStack]:
    nodes: list[WidgetStack] = []

    for root in roots:
        nodes.extend(root.iter_depth_first())

    return nodes


def _warn_bad_dimensions(
    roots: list[WidgetStack],
) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []

    for node in _iter_all_nodes(roots):
        if node.region.width <= 0:
            warnings.append(
                ValidationWarning(
                    node.path,
                    f"width is non-positive: {node.region.width}",
                )
            )

        if node.region.height <= 0:
            warnings.append(
                ValidationWarning(
                    node.path,
                    f"height is non-positive: {node.region.height}",
                )
            )

    return warnings


def _warn_duplicate_names(
    roots: list[WidgetStack],
) -> list[ValidationWarning]:
    by_name: dict[str, list[WidgetStack]] = defaultdict(list)

    for node in _iter_all_nodes(roots):
        by_name[node.name].append(node)

    warnings: list[ValidationWarning] = []

    for name, nodes in by_name.items():
        if len(nodes) <= 1:
            continue

        locations = ", ".join(node.path for node in nodes)

        for node in nodes:
            warnings.append(
                ValidationWarning(
                    node.path,
                    f"duplicate widget name {name!r}; locations: {locations}",
                )
            )

    return warnings


def _warn_duplicate_sibling_geometry(
    roots: list[WidgetStack],
) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []

    for node in _iter_all_nodes(roots):
        by_geometry: dict[tuple[int, int, int, int, str], list[WidgetStack]] = (
            defaultdict(list)
        )

        for child in node.children:
            key = (
                child.region.x_tl,
                child.region.y_tl,
                child.region.width,
                child.region.height,
                child.coord,
            )
            by_geometry[key].append(child)

        for geometry, children in by_geometry.items():
            if len(children) <= 1:
                continue

            names = ", ".join(child.name for child in children)
            x_tl, y_tl, width, height, coord = geometry

            for child in children:
                warnings.append(
                    ValidationWarning(
                        child.path,
                        "duplicate sibling geometry "
                        f"rel=({x_tl}, {y_tl}, {width}, {height}), "
                        f"coord={coord!r}; siblings: {names}",
                    )
                )

    return warnings


def _warn_parent_containment(
    roots: list[WidgetStack],
) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []

    for node in _iter_all_nodes(roots):
        for child in node.children:
            if child.coord != "parent":
                continue

            parent_region = node.region
            child_region = child.region

            if not parent_region.contains_region(child_region):
                warnings.append(
                    ValidationWarning(
                        child.path,
                        "child region is outside parent bounds "
                        f"child_rel={child_region.as_tuple()} "
                        f"parent_rel={parent_region.as_tuple()} "
                        "coord='parent'; "
                        "if this is a pop-out/cascading menu, set coord='popup'",
                    )
                )

    return warnings
