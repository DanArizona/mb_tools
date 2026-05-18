"""
Pseudo-widget layout helpers.

This package provides generic geometry, tree, YAML-loading, validation,
and reporting helpers for pseudo-widget layouts.
"""

from .index import flatten_widget_stacks
from .region import WidgetRegion
from .report import format_widget_tree, print_widget_tree
from .stack import VALID_COORD_MODES, WidgetStack
from .validate import ValidationWarning, validate_stacks
from .yaml_loader import WidgetYamlError, load_widget_stacks

__all__ = [
    "VALID_COORD_MODES",
    "ValidationWarning",
    "WidgetRegion",
    "WidgetStack",
    "WidgetYamlError",
    "flatten_widget_stacks",
    "format_widget_tree",
    "load_widget_stacks",
    "print_widget_tree",
    "validate_stacks",
]
