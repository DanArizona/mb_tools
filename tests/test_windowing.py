from __future__ import annotations

from unittest.mock import Mock

import pytest

from mb_tools import windowing
from mb_tools.pseudo_widgets import WidgetRegion, WidgetStack


class FakeWindow:
    """Small stand-in for a pygetwindow Window object."""

    def __init__(
        self,
        title: str,
        *,
        left: int = 0,
        top: int = 0,
        width: int = 100,
        height: int = 100,
        is_visible: bool = True,
        is_minimized: bool = False,
        activation_error: bool = False,
    ) -> None:
        self.title = title
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.isVisible = is_visible
        self.isMinimized = is_minimized
        self.activation_error = activation_error

        self.restore_calls = 0
        self.activate_calls = 0

    def restore(self) -> None:
        self.restore_calls += 1
        self.isMinimized = False

    def activate(self) -> None:
        self.activate_calls += 1

        if self.activation_error:
            raise RuntimeError("Synthetic activation failure")


def make_stack(
    name: str,
    *,
    width: int = 100,
    height: int = 100,
    x_tl: int = 0,
    y_tl: int = 0,
    coord: str = "screen",
) -> WidgetStack:
    return WidgetStack(
        name=name,
        region=WidgetRegion(
            width=width,
            height=height,
            x_tl=x_tl,
            y_tl=y_tl,
        ),
        coord=coord,
    )


def test_find_window_matches_prefix_case_insensitively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_empty_title = FakeWindow("")
    invalid_zero_width = FakeWindow(
        "Main@thinkorswim invalid",
        width=0,
    )
    unrelated = FakeWindow("Another application")
    expected = FakeWindow("Main@thinkorswim [build 1992]")

    monkeypatch.setattr(
        windowing.gw,
        "getAllWindows",
        lambda: [
            invalid_empty_title,
            invalid_zero_width,
            unrelated,
            expected,
        ],
    )

    found = windowing.find_window_by_title_prefix(
        "  main@THINKORSWIM  "
    )

    assert found is expected


def test_find_window_prefers_visible_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invisible = FakeWindow(
        "Watchlist Main@thinkorswim old",
        is_visible=False,
    )
    visible = FakeWindow(
        "Watchlist Main@thinkorswim [build 1992]",
        is_visible=True,
    )

    monkeypatch.setattr(
        windowing.gw,
        "getAllWindows",
        lambda: [invisible, visible],
    )

    found = windowing.find_window_by_title_prefix(
        "Watchlist Main@thinkorswim"
    )

    assert found is visible


@pytest.mark.parametrize(
    "title_prefix",
    [
        "",
        "   ",
        "Missing application",
    ],
)
def test_find_window_returns_none_when_no_match(
    monkeypatch: pytest.MonkeyPatch,
    title_prefix: str,
) -> None:
    monkeypatch.setattr(
        windowing.gw,
        "getAllWindows",
        lambda: [FakeWindow("Existing application")],
    )

    assert (
        windowing.find_window_by_title_prefix(title_prefix)
        is None
    )


def test_is_window_visible_by_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = FakeWindow("Main@thinkorswim [build 1992]")

    monkeypatch.setattr(
        windowing.gw,
        "getAllWindows",
        lambda: [expected],
    )

    assert windowing.is_window_visible_by_prefix(
        "Main@thinkorswim"
    )
    assert not windowing.is_window_visible_by_prefix(
        "Missing window"
    )


def test_bring_window_to_front_restores_minimized_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_window = FakeWindow(
        "Main@thinkorswim [build 1992]",
        is_minimized=True,
    )
    logger = Mock()

    monkeypatch.setattr(
        windowing,
        "find_window_by_title_prefix",
        lambda title_prefix: fake_window,
    )

    result = windowing.bring_window_to_front_by_prefix(
        "Main@thinkorswim",
        logger=logger,
    )

    assert result is True
    assert fake_window.restore_calls == 1
    assert fake_window.activate_calls == 1
    assert fake_window.isMinimized is False
    logger.info.assert_called_once()


def test_bring_window_to_front_returns_false_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = Mock()

    monkeypatch.setattr(
        windowing,
        "find_window_by_title_prefix",
        lambda title_prefix: None,
    )

    result = windowing.bring_window_to_front_by_prefix(
        "Missing window",
        logger=logger,
    )

    assert result is False
    logger.warning.assert_called_once()


def test_bring_window_to_front_handles_activation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_window = FakeWindow(
        "Broken application",
        activation_error=True,
    )
    logger = Mock()

    monkeypatch.setattr(
        windowing,
        "find_window_by_title_prefix",
        lambda title_prefix: fake_window,
    )

    result = windowing.bring_window_to_front_by_prefix(
        "Broken application",
        logger=logger,
    )

    assert result is False
    assert fake_window.activate_calls == 1
    logger.exception.assert_called_once()


def test_widget_helpers_resolve_root_and_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = make_stack("win_main")
    child = make_stack(
        "button_export",
        width=40,
        height=20,
        x_tl=10,
        y_tl=15,
        coord="parent",
    )
    root.add_child(child)

    widget_stacks = {
        "win_main": root,
        "button_export": child,
    }
    title_map = {
        "win_main": "Main@thinkorswim",
    }

    assert (
        windowing.get_root_title_prefix(
            "button_export",
            widget_stacks,
            title_map,
        )
        == "Main@thinkorswim"
    )

    visible_mock = Mock(return_value=True)
    front_mock = Mock(return_value=True)
    logger = Mock()

    monkeypatch.setattr(
        windowing,
        "is_window_visible_by_prefix",
        visible_mock,
    )
    monkeypatch.setattr(
        windowing,
        "bring_window_to_front_by_prefix",
        front_mock,
    )

    assert windowing.is_widget_window_visible(
        "button_export",
        widget_stacks,
        title_map,
    )

    assert windowing.bring_widget_window_to_front(
        "button_export",
        widget_stacks,
        title_map,
        logger=logger,
    )

    visible_mock.assert_called_once_with(
        "Main@thinkorswim"
    )
    front_mock.assert_called_once_with(
        "Main@thinkorswim",
        logger=logger,
    )


def test_update_root_window_positions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = make_stack(
        "win_main",
        width=1190,
        height=1080,
        x_tl=0,
        y_tl=0,
    )

    fake_window = FakeWindow(
        "Main@thinkorswim [build 1992]",
        left=730,
        top=0,
        width=1190,
        height=1080,
    )

    monkeypatch.setattr(
        windowing,
        "find_window_by_title_prefix",
        lambda title_prefix: fake_window,
    )

    windowing.update_root_window_positions(
        {"win_main": root},
        {"win_main": "Main@thinkorswim"},
    )

    assert root.region.x_tl == 730
    assert root.region.y_tl == 0

    # YAML dimensions remain unchanged.
    assert root.region.width == 1190
    assert root.region.height == 1080


def test_update_root_positions_logs_nonfatal_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_with_size_difference = make_stack(
        "win_main",
        width=100,
        height=100,
    )
    root_without_window = make_stack(
        "win_popup",
        width=200,
        height=100,
    )

    oversized_window = FakeWindow(
        "Main application",
        left=25,
        top=50,
        width=125,
        height=115,
    )

    def fake_find(title_prefix: str):
        if title_prefix == "Main application":
            return oversized_window
        return None

    monkeypatch.setattr(
        windowing,
        "find_window_by_title_prefix",
        fake_find,
    )

    logger = Mock()

    windowing.update_root_window_positions(
        {
            "win_main": root_with_size_difference,
            "win_popup": root_without_window,
        },
        {
            "win_main": "Main application",
            "win_popup": "Missing popup",
            "unknown_root": "Unknown application",
        },
        logger=logger,
        size_tolerance=4,
    )

    # The matching root is still updated despite the size warning.
    assert root_with_size_difference.region.x_tl == 25
    assert root_with_size_difference.region.y_tl == 50

    warning_formats = [
        call.args[0]
        for call in logger.warning.call_args_list
    ]

    assert any(
        "Window size differs from YAML" in message
        for message in warning_formats
    )
    assert any(
        "Could not find OS window" in message
        for message in warning_formats
    )
    assert any(
        "was not found in widget_stacks" in message
        for message in warning_formats
    )
