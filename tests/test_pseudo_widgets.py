from __future__ import annotations

from pathlib import Path

import pytest

from mb_tools.pseudo_widgets import (
    WidgetRegion,
    WidgetStack,
    WidgetYamlError,
    flatten_widget_stacks,
    load_widget_stacks,
    validate_stacks,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"
MINIMAL_LAYOUT = FIXTURES_DIR / "minimal_layout.yaml"
INVALID_LAYOUT = FIXTURES_DIR / "invalid_layout.yaml"


def test_load_minimal_layout() -> None:
    roots = load_widget_stacks(MINIMAL_LAYOUT)

    assert list(roots) == ["win_main", "win_popup"]

    win_main = roots["win_main"]
    win_popup = roots["win_popup"]

    assert win_main.name == "win_main"
    assert win_main.ptxt == "Main test window"
    assert win_main.coord == "screen"
    assert win_main.region.as_tuple() == (0, 0, 400, 300)

    assert win_popup.name == "win_popup"
    assert win_popup.ptxt == "Test popup"
    assert win_popup.region.as_tuple() == (600, 100, 200, 100)


def test_parent_child_structure_and_lookup() -> None:
    roots = load_widget_stacks(MINIMAL_LAYOUT)
    win_main = roots["win_main"]

    assert [child.name for child in win_main.children] == [
        "panel",
        "status",
    ]

    panel = win_main.find("panel")
    button_ok = win_main.find("button_ok")
    status = win_main.find("status")

    assert panel.parent is win_main
    assert button_ok.parent is panel
    assert status.parent is win_main

    assert button_ok.ptxt == "OK"

    assert panel.path == "win_main/panel"
    assert button_ok.path == "win_main/panel/button_ok"
    assert status.path == "win_main/status"

    assert button_ok.ancestry() == [
        "win_main",
        "panel",
        "button_ok",
    ]


def test_absolute_coordinate_calculations() -> None:
    roots = load_widget_stacks(MINIMAL_LAYOUT)
    win_main = roots["win_main"]

    panel = win_main.find("panel")
    button_ok = win_main.find("button_ok")
    status = win_main.find("status")

    # panel is relative to win_main.
    assert panel.absolute_region().as_tuple() == (
        10,
        20,
        200,
        100,
    )

    # button_ok uses coord="root", so its coordinates are relative
    # to the root rather than relative to panel.
    assert button_ok.absolute_region().as_tuple() == (
        50,
        60,
        80,
        30,
    )

    assert button_ok.absolute_center() == (90, 75)

    # status is relative to win_main.
    assert status.absolute_region().as_tuple() == (
        20,
        250,
        150,
        30,
    )


def test_flatten_widget_stacks() -> None:
    roots = load_widget_stacks(MINIMAL_LAYOUT)
    flat = flatten_widget_stacks(roots)

    assert list(flat) == [
        "win_main",
        "panel",
        "button_ok",
        "status",
        "win_popup",
    ]

    assert flat["win_main"] is roots["win_main"]
    assert flat["button_ok"] is roots["win_main"].find("button_ok")
    assert flat["win_popup"] is roots["win_popup"]


def test_valid_layout_has_no_validation_warnings() -> None:
    roots = load_widget_stacks(MINIMAL_LAYOUT)
    warnings = validate_stacks(roots)

    assert warnings == []


def test_invalid_layout_raises_yaml_error() -> None:
    with pytest.raises(
        WidgetYamlError,
        match="missing required field 'height'",
    ):
        load_widget_stacks(INVALID_LAYOUT)


def test_validation_reports_bad_dimensions_and_containment() -> None:
    root = WidgetStack(
        name="root",
        region=WidgetRegion(
            width=100,
            height=100,
            x_tl=0,
            y_tl=0,
        ),
        coord="screen",
    )

    bad_child = WidgetStack(
        name="bad_child",
        region=WidgetRegion(
            width=0,
            height=20,
            x_tl=120,
            y_tl=10,
        ),
        coord="parent",
    )

    root.add_child(bad_child)

    warnings = validate_stacks([root])
    messages = [str(warning) for warning in warnings]

    assert any(
        "width is non-positive: 0" in message
        for message in messages
    )

    assert any(
        "child region is outside parent bounds" in message
        for message in messages
    )


def test_duplicate_widget_names_are_rejected_when_flattening() -> None:
    root = WidgetStack(
        name="root",
        region=WidgetRegion(
            width=200,
            height=200,
            x_tl=0,
            y_tl=0,
        ),
        coord="screen",
    )

    first = WidgetStack(
        name="duplicate",
        region=WidgetRegion(
            width=20,
            height=20,
            x_tl=10,
            y_tl=10,
        ),
        coord="parent",
    )

    second = WidgetStack(
        name="duplicate",
        region=WidgetRegion(
            width=30,
            height=30,
            x_tl=50,
            y_tl=50,
        ),
        coord="parent",
    )

    root.add_child(first)
    root.add_child(second)

    with pytest.raises(
        ValueError,
        match="Duplicate widget name 'duplicate'",
    ):
        flatten_widget_stacks([root])


def test_validation_reports_duplicate_widget_names() -> None:
    root = WidgetStack(
        name="root",
        region=WidgetRegion(
            width=200,
            height=200,
            x_tl=0,
            y_tl=0,
        ),
        coord="screen",
    )

    root.add_child(
        WidgetStack(
            name="duplicate",
            region=WidgetRegion(
                width=20,
                height=20,
                x_tl=10,
                y_tl=10,
            ),
            coord="parent",
        )
    )

    root.add_child(
        WidgetStack(
            name="duplicate",
            region=WidgetRegion(
                width=30,
                height=30,
                x_tl=50,
                y_tl=50,
            ),
            coord="parent",
        )
    )

    warnings = validate_stacks([root])
    duplicate_warnings = [
        warning
        for warning in warnings
        if "duplicate widget name" in warning.message
    ]

    assert len(duplicate_warnings) == 2
    assert all(
        warning.widget_path.startswith("root/duplicate")
        for warning in duplicate_warnings
    )
