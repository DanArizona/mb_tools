"""
Geometry primitives for pseudo-widget layouts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WidgetRegion:
    """
    Rectangular widget region.

    Coordinates are top-left based. The coordinate frame depends on how
    the owning WidgetStack interprets the region.
    """

    width: int
    height: int
    x_tl: int
    y_tl: int

    @property
    def x_br(self) -> int:
        """Right edge coordinate."""
        return self.x_tl + self.width

    @property
    def y_br(self) -> int:
        """Bottom edge coordinate."""
        return self.y_tl + self.height

    @property
    def center(self) -> tuple[int, int]:
        """Center point of the region."""
        return (
            self.x_tl + self.width // 2,
            self.y_tl + self.height // 2,
        )

    def translated(self, dx: int, dy: int) -> "WidgetRegion":
        """Return this region shifted by dx, dy."""
        return WidgetRegion(
            width=self.width,
            height=self.height,
            x_tl=self.x_tl + dx,
            y_tl=self.y_tl + dy,
        )

    def contains_region(self, other: "WidgetRegion") -> bool:
        """Return True if this region fully contains another region."""
        return (
            other.x_tl >= self.x_tl
            and other.y_tl >= self.y_tl
            and other.x_br <= self.x_br
            and other.y_br <= self.y_br
        )

    def as_tuple(self) -> tuple[int, int, int, int]:
        """
        Return region as x_tl, y_tl, width, height.
        """
        return self.x_tl, self.y_tl, self.width, self.height
