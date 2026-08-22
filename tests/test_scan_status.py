from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mb_tools.scan_status import (
    format_human_report,
    main,
    read_scan_status,
    report_as_json,
)


TEST_NOW = datetime(
    2026,
    7,
    26,
    9,
    0,
    0,
    tzinfo=timezone.utc,
)


def create_command_root(tmp_path: Path) -> Path:
    root = tmp_path / "scan-control"
    (root / "status").mkdir(parents=True)
    return root


def write_heartbeat(
    root: Path,
    *,
    heartbeat_at: datetime = TEST_NOW,
    loop_state: str = "idle",
    running: bool = True,
    paused: bool = False,
    shutdown_requested: bool = False,
) -> Path:
    heartbeat_path = (
        root / "status" / "scanner_heartbeat.json"
    )

    payload = {
        "schema_version": 1,
        "application": "ToS_scanner",
        "host": "El-Cheapo",
        "pid": 25156,
        "started_at_utc": "2026-07-26T08:00:00Z",
        "heartbeat_at_utc": (
            heartbeat_at
            .astimezone(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        ),
        "heartbeat_sequence": 25,
        "heartbeat_interval_s": 5.0,
        "loop_state": loop_state,
        "running": running,
        "paused": paused,
        "shutdown_requested": shutdown_requested,
        "current_job": None,
        "last_job": {
            "kind": "resume",
            "command_id": "test-resume-command",
            "ok": True,
            "message": "Scanner resumed.",
            "error": None,
        },
    }

    heartbeat_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    return heartbeat_path


def test_read_scan_status_reports_healthy(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(root)

    report = read_scan_status(
        root=root,
        stale_after_s=30.0,
        now_utc=TEST_NOW,
    )

    assert report.status == "HEALTHY"
    assert report.age_seconds == 0.0
    assert report.payload is not None
    assert report.payload["host"] == "El-Cheapo"


def test_read_scan_status_clamps_future_heartbeat_age(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(
        root,
        heartbeat_at=TEST_NOW + timedelta(seconds=2),
    )

    report = read_scan_status(
        root=root,
        stale_after_s=30.0,
        now_utc=TEST_NOW,
    )

    assert report.status == "HEALTHY"
    assert report.age_seconds == 0.0


def test_read_scan_status_reports_paused(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(
        root,
        loop_state="paused",
        paused=True,
    )

    report = read_scan_status(
        root=root,
        now_utc=TEST_NOW,
    )

    assert report.status == "PAUSED"


def test_read_scan_status_reports_busy(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(
        root,
        loop_state="busy",
    )

    report = read_scan_status(
        root=root,
        now_utc=TEST_NOW,
    )

    assert report.status == "BUSY"


def test_read_scan_status_reports_stopped(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(
        root,
        heartbeat_at=TEST_NOW - timedelta(hours=1),
        loop_state="stopped",
        running=False,
        shutdown_requested=True,
    )

    report = read_scan_status(
        root=root,
        stale_after_s=30.0,
        now_utc=TEST_NOW,
    )

    assert report.status == "STOPPED"


def test_read_scan_status_reports_stale(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(
        root,
        heartbeat_at=TEST_NOW - timedelta(seconds=31),
    )

    report = read_scan_status(
        root=root,
        stale_after_s=30.0,
        now_utc=TEST_NOW,
    )

    assert report.status == "STALE"
    assert report.age_seconds == 31.0


def test_read_scan_status_reports_missing(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)

    report = read_scan_status(
        root=root,
        now_utc=TEST_NOW,
    )

    assert report.status == "MISSING"
    assert report.payload is None


def test_read_scan_status_reports_invalid_json(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    heartbeat_path = (
        root / "status" / "scanner_heartbeat.json"
    )
    heartbeat_path.write_text(
        "{not valid json}\n",
        encoding="utf-8",
    )

    report = read_scan_status(
        root=root,
        now_utc=TEST_NOW,
    )

    assert report.status == "INVALID"


def test_main_warning_returns_zero(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = create_command_root(tmp_path)

    heartbeat_path = write_heartbeat(
        root,
        heartbeat_at=datetime.now(
            timezone.utc
        ),
        loop_state="exports_suspended",
    )

    payload = json.loads(
        heartbeat_path.read_text(
            encoding="utf-8"
        )
    )

    payload.update(
        {
            "exports_suspended": True,
            "state_health": "WARNING",
            "suspension_age_seconds": 90.0,
        }
    )

    heartbeat_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "MB_SCAN_CONTROL",
        str(root),
    )

    result = main([])

    assert result == 0

    output = capsys.readouterr().out

    assert (
        "Scanner status : WARNING"
        in output
    )


def test_main_degraded_returns_one(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = create_command_root(tmp_path)

    heartbeat_path = write_heartbeat(
        root,
        heartbeat_at=datetime.now(
            timezone.utc
        ),
        loop_state="exports_suspended",
    )

    payload = json.loads(
        heartbeat_path.read_text(
            encoding="utf-8"
        )
    )

    payload.update(
        {
            "exports_suspended": True,
            "state_health": "DEGRADED",
            "suspension_age_seconds": 120.0,
        }
    )

    heartbeat_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "MB_SCAN_CONTROL",
        str(root),
    )

    result = main([])

    assert result == 1

    output = capsys.readouterr().out

    assert (
        "Scanner status : DEGRADED"
        in output
    )


def test_main_reads_root_from_environment(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(
        root,
        heartbeat_at=datetime.now(timezone.utc),
    )
    monkeypatch.setenv("MB_SCAN_CONTROL", str(root))

    result = main([])

    assert result == 0

    output = capsys.readouterr().out
    assert "Scanner status : HEALTHY" in output
    assert "Host           : El-Cheapo" in output
    assert "Last command   : resume" in output


def test_main_outputs_json(
    tmp_path: Path,
    capsys,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(
        root,
        heartbeat_at=datetime.now(timezone.utc),
    )

    result = main(
        [
            "--root",
            str(root),
            "--json",
        ]
    )

    assert result == 0

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "HEALTHY"
    assert output["heartbeat"]["host"] == "El-Cheapo"


def test_report_formatters(
    tmp_path: Path,
) -> None:
    root = create_command_root(tmp_path)
    write_heartbeat(root)

    report = read_scan_status(
        root=root,
        now_utc=TEST_NOW,
    )

    human_output = format_human_report(report)
    json_output = json.loads(report_as_json(report))

    assert "Scanner status : HEALTHY" in human_output
    assert "Sequence       : 25" in human_output
    assert json_output["status"] == "HEALTHY"
