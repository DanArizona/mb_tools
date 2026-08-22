from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from mb_tools.scan_command import (
    ScanCommandError,
    resolve_command_root,
)


DEFAULT_STALE_AFTER_S = 30.0

OPERATIONAL_STATUSES = frozenset(
    {
        "HEALTHY",
        "PAUSED",
        "BUSY",
        "WAITING",
        "WARNING",
    }
)


@dataclass(frozen=True)
class ScanStatusReport:
    status: str
    heartbeat_path: Path
    detail: str
    age_seconds: float | None = None
    payload: dict[str, Any] | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mb-scan-status",
        description=(
            "Read and interpret a ToS scanner heartbeat file."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        help=(
            "Scanner command root. Defaults to the MB_SCAN_CONTROL "
            "environment variable."
        ),
    )

    parser.add_argument(
        "--stale-after",
        type=float,
        default=DEFAULT_STALE_AFTER_S,
        metavar="SECONDS",
        help=(
            "Maximum heartbeat age before reporting STALE. "
            f"Default: {DEFAULT_STALE_AFTER_S:g}."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the interpreted status as JSON.",
    )

    return parser


def parse_utc_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "heartbeat_at_utc must be a non-empty string."
        )

    timestamp_text = value.strip()

    if timestamp_text.endswith("Z"):
        timestamp_text = timestamp_text[:-1] + "+00:00"
    timestamp = datetime.fromisoformat(timestamp_text)

    if timestamp.tzinfo is None:
        raise ValueError(
            "heartbeat_at_utc must include a timezone."
        )

    return timestamp.astimezone(timezone.utc)


def read_scan_status(
    *,
    root: Path,
    stale_after_s: float = DEFAULT_STALE_AFTER_S,
    now_utc: datetime | None = None,
) -> ScanStatusReport:
    if stale_after_s <= 0:
        raise ValueError(
            "stale_after_s must be greater than zero."
        )

    root = Path(root)
    heartbeat_path = (
        root / "status" / "scanner_heartbeat.json"
    )

    try:
        root.stat()
    except FileNotFoundError:
        return ScanStatusReport(
            status="UNREACHABLE",
            heartbeat_path=heartbeat_path,
            detail=f"Command root does not exist: {root}",
        )
    except OSError as exc:
        return ScanStatusReport(
            status="UNREACHABLE",
            heartbeat_path=heartbeat_path,
            detail=f"Cannot access command root: {exc}",
        )

    if not root.is_dir():
        return ScanStatusReport(
            status="UNREACHABLE",
            heartbeat_path=heartbeat_path,
            detail=f"Command root is not a directory: {root}",
        )

    try:
        heartbeat_text = heartbeat_path.read_text(
            encoding="utf-8"
        )
    except FileNotFoundError:
        return ScanStatusReport(
            status="MISSING",
            heartbeat_path=heartbeat_path,
            detail="Heartbeat file does not exist.",
        )
    except OSError as exc:
        return ScanStatusReport(
            status="UNREACHABLE",
            heartbeat_path=heartbeat_path,
            detail=f"Cannot read heartbeat file: {exc}",
        )

    try:
        payload = json.loads(heartbeat_text)
    except json.JSONDecodeError as exc:
        return ScanStatusReport(
            status="INVALID",
            heartbeat_path=heartbeat_path,
            detail=f"Heartbeat file contains invalid JSON: {exc}",
        )

    if not isinstance(payload, dict):
        return ScanStatusReport(
            status="INVALID",
            heartbeat_path=heartbeat_path,
            detail="Heartbeat JSON must contain an object.",
        )

    try:
        heartbeat_at = parse_utc_timestamp(
            payload.get("heartbeat_at_utc")
        )
    except (TypeError, ValueError) as exc:
        return ScanStatusReport(
            status="INVALID",
            heartbeat_path=heartbeat_path,
            detail=f"Invalid heartbeat timestamp: {exc}",
            payload=payload,
        )

    effective_now = now_utc or datetime.now(timezone.utc)
    if effective_now.tzinfo is None:
        raise ValueError("now_utc must include a timezone.")

    effective_now = effective_now.astimezone(timezone.utc)
    age_seconds = max(
        0.0,
        (effective_now - heartbeat_at).total_seconds(),
    )

    loop_state = str(
        payload.get("loop_state", "")
    ).strip().lower()

    shutdown_requested = bool(
        payload.get("shutdown_requested", False)
    )
    paused = bool(payload.get("paused", False))

    # Preserve an explicit clean stop even after its final heartbeat ages.
    if shutdown_requested or loop_state == "stopped":
        return ScanStatusReport(
            status="STOPPED",
            heartbeat_path=heartbeat_path,
            detail="Scanner published a stopped state.",
            age_seconds=age_seconds,
            payload=payload,
        )

    if age_seconds > stale_after_s:
        return ScanStatusReport(
            status="STALE",
            heartbeat_path=heartbeat_path,
            detail=(
                f"Heartbeat is older than "
                f"{stale_after_s:g} seconds."
            ),
            age_seconds=age_seconds,
            payload=payload,
        )

    if paused or loop_state == "paused":
        status = "PAUSED"
        detail = "Scanner heartbeat is current and paused."
    elif loop_state == "busy":
        status = "BUSY"
        detail = "Scanner heartbeat is current and processing a job."
    elif loop_state == "waiting_for_operator":
        status = "WAITING"
        detail = "Scanner is waiting for operator confirmation."
    elif loop_state == "exports_suspended":
        state_health = str(
            payload.get(
                "state_health",
                "NORMAL",
            )
        ).strip().upper()

        if state_health == "DEGRADED":
            status = "DEGRADED"
            detail = (
                "Scanner heartbeat is current; "
                "exports are suspended and "
                "state health is DEGRADED."
            )
        elif state_health == "WARNING":
            status = "WARNING"
            detail = (
                "Scanner heartbeat is current; "
                "exports are suspended and "
                "state health is WARNING."
            )
        else:
            status = "HEALTHY"
            detail = (
                "Scanner heartbeat is current; "
                "exports are suspended."
            )
    elif loop_state == "idle":
        status = "HEALTHY"
        detail = "Scanner heartbeat is current."
    else:
        status = "UNKNOWN"
        detail = (
            "Heartbeat is current, but loop_state is not recognized: "
            f"{loop_state or '(missing)'}"
        )

    return ScanStatusReport(
        status=status,
        heartbeat_path=heartbeat_path,
        detail=detail,
        age_seconds=age_seconds,
        payload=payload,
    )


def yes_no(value: object) -> str:
    return "yes" if bool(value) else "no"


def format_human_report(
    report: ScanStatusReport,
) -> str:
    payload = report.payload or {}

    lines = [
        f"Scanner status : {report.status}",
        f"Detail         : {report.detail}",
        f"Heartbeat file : {report.heartbeat_path}",
    ]

    if report.age_seconds is not None:
        lines.append(
            f"Heartbeat age  : {report.age_seconds:.1f} seconds"
        )

    if payload:
        lines.extend(
            [
                f"Host           : {payload.get('host', '(unknown)')}",
                (
                    "Loop state     : "
                    f"{payload.get('loop_state', '(unknown)')}"
                ),
                (
                    "Running        : "
                    f"{yes_no(payload.get('running', False))}"
                ),
                (
                    "Paused         : "
                    f"{yes_no(payload.get('paused', False))}"
                ),
                (
                    "Exports suspended: "
                    f"{yes_no(payload.get('exports_suspended', False))}"
                ),
                (
                    "Sequence       : "
                    f"{payload.get('heartbeat_sequence', '(unknown)')}"
                ),
                f"PID            : {payload.get('pid', '(unknown)')}",
            ]
        )
        state_health = payload.get(
            "state_health"
        )
        if state_health is not None:
            lines.append(
                "State health    : "
                f"{state_health}"
            )

        suspended_since = payload.get(
            "exports_suspended_since_utc"
        )
        if suspended_since is not None:
            lines.append(
                "Suspended since : "
                f"{suspended_since}"
            )

        suspension_age = payload.get(
            "suspension_age_seconds"
        )
        if suspension_age is not None:
            lines.append(
                "Suspension age  : "
                f"{suspension_age} seconds"
            )

        suspension_command = payload.get(
            "suspension_command_id"
        )
        if suspension_command is not None:
            lines.append(
                "Suspension command: "
                f"{suspension_command}"
            )

        current_job = payload.get("current_job")
        if isinstance(current_job, dict):
            lines.append(
                "Current job    : "
                f"{current_job.get('kind', '(unknown)')}"
            )

        last_job = payload.get("last_job")
        if isinstance(last_job, dict):
            lines.extend(
                [
                    (
                        "Last command   : "
                        f"{last_job.get('kind', '(unknown)')}"
                    ),
                    (
                        "Last result    : "
                        f"{last_job.get('message', '(none)')}"
                    ),
                ]
            )

    return "\n".join(lines)


def report_as_json(
    report: ScanStatusReport,
) -> str:
    output = {
        "status": report.status,
        "detail": report.detail,
        "heartbeat_path": str(report.heartbeat_path),
        "age_seconds": report.age_seconds,
        "heartbeat": report.payload,
    }

    return json.dumps(
        output,
        indent=2,
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.stale_after <= 0:
        parser.error("--stale-after must be greater than zero.")

    try:
        root = resolve_command_root(args.root)
    except ScanCommandError as exc:
        print(f"mb-scan-status: error: {exc}", file=sys.stderr)
        return 2

    report = read_scan_status(
        root=root,
        stale_after_s=args.stale_after,
    )

    if args.json:
        print(report_as_json(report))
    else:
        print(format_human_report(report))

    if report.status in OPERATIONAL_STATUSES:
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
