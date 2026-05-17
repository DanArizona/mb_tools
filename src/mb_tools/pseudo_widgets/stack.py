"""
Pseudo-widget tree model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from .region import WidgetRegion


VALID_COORD_MODES = {"parent", "root", "screen", "popup"}


@dataclass
class WidgetStack:
    """
    Logical pseudo-widget node.

    The node owns identity/tree information. Its WidgetRegion owns only
    geometry.
    """

    name: str
    region: WidgetRegion
    ptxt: str = ""
    coord: str = "parent"
    parent: "WidgetStack | None" = None
    children: list["WidgetStack"] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.coord not in VALID_COORD_MODES:
            raise ValueError(
                f"Invalid coord mode {self.coord!r} for widget {self.name!r}. "
                f"Expected one of {sorted(VALID_COORD_MODES)}."
            )

    def add_child(self, child: "WidgetStack") -> None:
        """Attach a child node."""
        child.parent = self
        self.children.append(child)

    def iter_depth_first(self) -> Iterator["WidgetStack"]:
        """Yield this node and descendants depth-first."""
        yield self
        for child in self.children:
            yield from child.iter_depth_first()

    def ancestry(self) -> list[str]:
        """Return names from root to this node."""
        nodes: list[str] = []
        current: WidgetStack | None = self

        while current is not None:
            nodes.append(current.name)
            current = current.parent

        return list(reversed(nodes))

    def root(self) -> "WidgetStack":
        """Return this node's root."""
        current = self

        while current.parent is not None:
            current = current.parent

        return current

    def absolute_region(self) -> WidgetRegion:
        """
        Return the region in screen coordinates.

        Coordinate modes:

        parent:
            Region is relative to parent absolute top-left.

        popup:
            Same calculation as parent for now, but validators can treat
            containment differently.

        root:
            Region is relative to root absolute top-left.

        screen:
            Region is already absolute screen coordinates.
        """
        if self.parent is None:
            return self.region

        if self.coord == "screen":
            return self.region

        if self.coord == "root":
            root_abs = self.root().absolute_region()
            return self.region.translated(root_abs.x_tl, root_abs.y_tl)

        # parent and popup both use parent-relative coordinates
        parent_abs = self.parent.absolute_region()
        return self.region.translated(parent_abs.x_tl, parent_abs.y_tl)

    def absolute_center(self) -> tuple[int, int]:
        """Return center point in screen coordinates."""
        return self.absolute_region().center

    def find(self, name: str) -> "WidgetStack":
        """
        Find one descendant by name.

        Raises KeyError if no match is found.
        """
        for node in self.iter_depth_first():
            if node.name == name:
                return node

        raise KeyError(name)

    def find_all(self, name: str) -> list["WidgetStack"]:
        """Find all descendants with a given name."""
        return [
            node
            for node in self.iter_depth_first()
            if node.name == name
        ]

    @property
    def path(self) -> str:
        """Return root-to-node path as slash-separated text."""
        return "/".join(self.ancestry())
