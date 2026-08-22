from __future__ import annotations

import json
from datetime import datetime, timezone
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
    read_scan_status,
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


def test_human_status_reports_suspension_health_metadata(
    tmp_path: Path,
) -> None:
    report = ScanStatusReport(
        status="WARNING",
        heartbeat_path=tmp_path / "heartbeat.json",
        detail=(
            "Scanner heartbeat is current; "
            "exports are suspended and "
            "state health is WARNING."
        ),
        age_seconds=1.25,
        payload={
            "host": "El-Cheapo",
            "loop_state": "exports_suspended",
            "running": True,
            "paused": False,
            "exports_suspended": True,
            "exports_suspended_since_utc": (
                "2026-08-22T04:58:30Z"
            ),
            "suspension_age_seconds": 90.0,
            "suspension_command_id": (
                "suspend-warning-test"
            ),
            "state_health": "WARNING",
            "heartbeat_sequence": 10,
            "pid": 1234,
        },
    )

    text = format_human_report(report)

    assert "State health    : WARNING" in text
    assert (
        "Suspended since : "
        "2026-08-22T04:58:30Z"
        in text
    )
    assert (
        "Suspension age  : 90.0 seconds"
        in text
    )
    assert (
        "Suspension command: "
        "suspend-warning-test"
        in text
    )


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


def test_exports_suspended_warning_is_reported(
    tmp_path: Path,
) -> None:
    root = tmp_path / "scan-control"
    status_dir = root / "status"
    status_dir.mkdir(parents=True)

    now_utc = datetime(
        2026,
        8,
        22,
        5,
        0,
        0,
        tzinfo=timezone.utc,
    )

    heartbeat_path = (
        status_dir / "scanner_heartbeat.json"
    )

    heartbeat_path.write_text(
        json.dumps(
            {
                "heartbeat_at_utc": (
                    now_utc.isoformat()
                ),
                "loop_state": (
                    "exports_suspended"
                ),
                "running": True,
                "paused": False,
                "exports_suspended": True,
                "exports_suspended_since_utc": (
                    "2026-08-22T04:58:30Z"
                ),
                "suspension_age_seconds": 90.0,
                "suspension_command_id": (
                    "suspend-warning-test"
                ),
                "state_health": "WARNING",
                "shutdown_requested": False,
            }
        ),
        encoding="utf-8",
    )

    report = read_scan_status(
        root=root,
        now_utc=now_utc,
    )

    assert report.status == "WARNING"
    assert (
        report.payload["state_health"]
        == "WARNING"
    )


def test_exports_suspended_degraded_is_reported(
    tmp_path: Path,
) -> None:
    root = tmp_path / "scan-control"
    status_dir = root / "status"
    status_dir.mkdir(parents=True)

    now_utc = datetime(
        2026,
        8,
        22,
        5,
        0,
        0,
        tzinfo=timezone.utc,
    )

    heartbeat_path = (
        status_dir / "scanner_heartbeat.json"
    )

    heartbeat_path.write_text(
        json.dumps(
            {
                "heartbeat_at_utc": (
                    now_utc.isoformat()
                ),
                "loop_state": (
                    "exports_suspended"
                ),
                "running": True,
                "paused": False,
                "exports_suspended": True,
                "exports_suspended_since_utc": (
                    "2026-08-22T04:57:00Z"
                ),
                "suspension_age_seconds": 120.0,
                "suspension_command_id": (
                    "suspend-degraded-test"
                ),
                "state_health": "DEGRADED",
                "shutdown_requested": False,
            }
        ),
        encoding="utf-8",
    )

    report = read_scan_status(
        root=root,
        now_utc=now_utc,
    )

    assert report.status == "DEGRADED"
    assert (
        report.payload["state_health"]
        == "DEGRADED"
    )


def test_exports_suspended_loop_state_is_operational(
    tmp_path: Path,
) -> None:
    root = tmp_path / "scan-control"
    status_dir = root / "status"
    status_dir.mkdir(parents=True)

    now_utc = datetime(
        2026,
        8,
        7,
        20,
        0,
        0,
        tzinfo=timezone.utc,
    )
    heartbeat_path = (
        status_dir / "scanner_heartbeat.json"
    )
    heartbeat_path.write_text(
        json.dumps(
            {
                "heartbeat_at_utc": (
                    now_utc.isoformat()
                ),
                "loop_state": (
                    "exports_suspended"
                ),
                "running": True,
                "paused": False,
                "exports_suspended": True,
                "shutdown_requested": False,
            }
        ),
        encoding="utf-8",
    )

    report = read_scan_status(
        root=root,
        now_utc=now_utc,
    )

    assert report.status == "HEALTHY"
    assert report.detail == (
        "Scanner heartbeat is current; "
        "exports are suspended."
    )
    assert (
        report.payload["exports_suspended"]
        is True
    )
