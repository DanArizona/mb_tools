from __future__ import annotations

import json
from pathlib import Path

import pytest

from mb_tools.scan_command import (
    COMMAND_PAYLOADS,
    build_parser,
    main,
)
from mb_tools.scan_status import (
    ScanStatusReport,
    format_human_report,
    report_as_json,
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


@pytest.mark.parametrize(
    ("command", "command_id"),
    [
        (
            "suspend_exports",
            "test-suspend-exports-0001",
        ),
        (
            "resume_exports",
            "test-resume-exports-0001",
        ),
    ],
)
def test_export_control_command_is_published(
    tmp_path: Path,
    command: str,
    command_id: str,
) -> None:
    root = create_command_root(tmp_path)

    result = main(
        [
            command,
            "--root",
            str(root),
            "--command-id",
            command_id,
        ]
    )

    assert result == 0

    command_path = (
        root / "incoming" / f"{command_id}.json"
    )
    payload = json.loads(
        command_path.read_text(encoding="utf-8")
    )

    assert payload == {"command": command}


def test_parser_exposes_export_control_commands() -> None:
    parser = build_parser()

    suspend_args = parser.parse_args(
        ["suspend_exports"]
    )
    resume_args = parser.parse_args(
        ["resume_exports"]
    )

    assert suspend_args.command == "suspend_exports"
    assert resume_args.command == "resume_exports"
    assert COMMAND_PAYLOADS["suspend_exports"] == {
        "command": "suspend_exports"
    }
    assert COMMAND_PAYLOADS["resume_exports"] == {
        "command": "resume_exports"
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, "Exports suspended: yes"),
        (False, "Exports suspended: no"),
    ],
)
def test_human_status_reports_export_suspension(
    tmp_path: Path,
    value: bool,
    expected: str,
) -> None:
    report = ScanStatusReport(
        status="HEALTHY",
        heartbeat_path=tmp_path / "heartbeat.json",
        detail="Scanner heartbeat is current.",
        age_seconds=1.25,
        payload={
            "host": "El-Cheapo",
            "loop_state": "idle",
            "running": True,
            "paused": False,
            "exports_suspended": value,
            "heartbeat_sequence": 9,
            "pid": 1234,
        },
    )

    text = format_human_report(report)

    assert expected in text
    assert "Scanner status : HEALTHY" in text


def test_json_status_preserves_export_suspension(
    tmp_path: Path,
) -> None:
    report = ScanStatusReport(
        status="HEALTHY",
        heartbeat_path=tmp_path / "heartbeat.json",
        detail="Scanner heartbeat is current.",
        payload={
            "exports_suspended": True,
        },
    )

    output = json.loads(report_as_json(report))

    assert (
        output["heartbeat"]["exports_suspended"]
        is True
    )
