# src/mb_tools/pwidget_tree.py

"""
Command-line tool for printing pseudo-widget YAML trees.

Example:
    mb-pwidget-tree layout_scanner3_v1p0.yaml

    mb-pwidget-tree layout_scanner3_v1p0.yaml --root win_main

    mb-pwidget-tree layout_scanner3_v1p0.yaml --no-abs --no-text
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mb_tools.pseudo_widgets.report import format_widget_tree
from mb_tools.pseudo_widgets.yaml_loader import WidgetYamlError, load_widget_stacks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print the tree structure of a pseudo-widget YAML file."
    )

    parser.add_argument(
        "yaml_file",
        type=Path,
        help="Path to the pseudo-widget YAML layout file.",
    )

    parser.add_argument(
        "--root",
        help=(
            "Print only one top-level root widget, such as win_main. "
            "If omitted, all roots are printed."
        ),
    )

    parser.add_argument(
        "--no-abs",
        action="store_true",
        help="Do not print absolute coordinates and center points.",
    )

    parser.add_argument(
        "--no-text",
        action="store_true",
        help="Do not print ptxt/text labels.",
    )

    parser.add_argument(
        "--roots-only",
        action="store_true",
        help="Print only the names of the top-level root widgets.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    yaml_path: Path = args.yaml_file

    try:
        stacks = load_widget_stacks(yaml_path)
    except FileNotFoundError:
        parser.error(f"YAML file not found: {yaml_path}")
    except WidgetYamlError as exc:
        parser.error(f"Could not load pseudo-widget YAML: {exc}")

    if args.roots_only:
        for name in stacks:
            print(name)
        return 0

    if args.root:
        try:
            stacks_to_print = {args.root: stacks[args.root]}
        except KeyError:
            known_roots = ", ".join(stacks)
            parser.error(
                f"Root widget {args.root!r} was not found. "
                f"Known roots: {known_roots}"
            )
    else:
        stacks_to_print = stacks

    report = format_widget_tree(
        stacks_to_print,
        show_abs=not args.no_abs,
        show_text=not args.no_text,
    )

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
