from __future__ import annotations

import json
from pathlib import Path

from mb_tools.scan_command import (
    find_command_location,
    main,
    publish_command,
    wait_for_result,
)


def create_command_root(tmp_path: Path) -> Path:
    root = tmp_path / "scan-control"

    for directory_name in (
        "incoming",
        "processing",
        "processed",
        "failed",
    ):
        (root / directory_name).mkdir(parents=True)

    return root


def test_publish_command_uses_json_and_removes_temporary_file(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)

    published_path = publish_command(
        root=root,
        command_id="test-start-0001",
        payload={"command": "start"},
    )

    assert published_path == (
        root / "incoming" / "test-start-0001.json"
    )
    assert published_path.exists()
    assert not (
        root / "incoming" / "test-start-0001.tmp"
    ).exists()

    payload = json.loads(published_path.read_text(encoding="utf-8"))
    assert payload == {"command": "start"}


def test_find_command_location_reports_processing(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    command_path = root / "processing" / "test-start-0002.json"
    command_path.write_text(
        '{"command": "start"}\n',
        encoding="utf-8",
    )

    result = find_command_location(
        root=root,
        command_id="test-start-0002",
    )

    assert result == ("processing", command_path)


def test_wait_for_result_finds_processed_command(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    command_path = root / "processed" / "test-start-0003.json"
    command_path.write_text(
        '{"command": "start"}\n',
        encoding="utf-8",
    )

    result = wait_for_result(
        root=root,
        command_id="test-start-0003",
        timeout=0.1,
        poll_interval=0.01,
    )

    assert result == ("processed", command_path)


def test_wait_for_result_finds_failed_command(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    command_path = root / "failed" / "test-stop-0001.json"
    command_path.write_text(
        '{"command": "stop"}\n',
        encoding="utf-8",
    )

    result = wait_for_result(
        root=root,
        command_id="test-stop-0001",
        timeout=0.1,
        poll_interval=0.01,
    )

    assert result == ("failed", command_path)


def test_main_publishes_start_command_from_environment(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = create_command_root(tmp_path)
    monkeypatch.setenv("MB_SCAN_CONTROL", str(root))

    result = main(
        [
            "start",
            "--command-id",
            "test-main-start-0001",
        ]
    )

    assert result == 0

    command_path = (
        root / "incoming" / "test-main-start-0001.json"
    )
    assert command_path.exists()

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    assert payload == {"command": "start"}

    output = capsys.readouterr().out
    assert "test-main-start-0001" in output
    assert "start" in output


def test_main_publishes_stop_command_using_explicit_root(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)

    result = main(
        [
            "stop",
            "--root",
            str(root),
            "--command-id",
            "test-main-stop-0001",
        ]
    )

    assert result == 0

    command_path = (
        root / "incoming" / "test-main-stop-0001.json"
    )
    payload = json.loads(command_path.read_text(encoding="utf-8"))

    assert payload == {"command": "stop"}


def test_main_publishes_pause_command_using_explicit_root(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    command_id = "test-main-pause-0001"

    result = main(
        [
            "pause",
            "--root",
            str(root),
            "--command-id",
            command_id,
        ]
    )

    assert result == 0

    command_path = root / "incoming" / f"{command_id}.json"
    assert command_path.exists()

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    assert payload == {"command": "pause"}


def test_main_publishes_resume_command_using_explicit_root(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    command_id = "test-main-resume-0001"

    result = main(
        [
            "resume",
            "--root",
            str(root),
            "--command-id",
            command_id,
        ]
    )

    assert result == 0

    command_path = root / "incoming" / f"{command_id}.json"
    assert command_path.exists()

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    assert payload == {"command": "resume"}


def test_main_publishes_export_wl_command_using_explicit_root(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    command_id = "test-main-export-wl-0001"

    result = main(
        [
            "export_wl",
            "--root",
            str(root),
            "--command-id",
            command_id,
        ]
    )

    assert result == 0

    command_path = root / "incoming" / f"{command_id}.json"
    assert command_path.exists()

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    assert payload == {"command": "export_wl"}


def test_main_publishes_replace_wl_symbols_command(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    command_id = "test-main-replace-wl-symbols-0001"

    result = main(
        [
            "replace_wl_symbols",
            "--symbols",
            "aapl,msft",
            "NVDA",
            "aapl",
            "--root",
            str(root),
            "--command-id",
            command_id,
        ]
    )

    assert result == 0

    command_path = root / "incoming" / f"{command_id}.json"
    assert command_path.exists()

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    assert payload == {
        "command": "replace_wl_symbols",
        "symbols": ["AAPL", "MSFT", "NVDA"],
    }


def test_main_publishes_add_wl_symbols_command(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    command_id = "test-main-add-wl-symbols-0001"

    result = main(
        [
            "add_wl_symbols",
            "--symbols",
            "tsla",
            "AMD,NVDA",
            "--root",
            str(root),
            "--command-id",
            command_id,
        ]
    )

    assert result == 0

    command_path = root / "incoming" / f"{command_id}.json"
    assert command_path.exists()

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    assert payload == {
        "command": "add_wl_symbols",
        "symbols": ["TSLA", "AMD", "NVDA"],
    }
