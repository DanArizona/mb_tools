from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Sequence


ENV_SCAN_CONTROL = "MB_SCAN_CONTROL"

COMMAND_PAYLOADS: dict[str, dict[str, str]] = {
    "start": {"command": "start"},
    "stop": {"command": "stop"},
    "pause": {"command": "pause"},
    "resume": {"command": "resume"},
}

REQUIRED_DIRECTORIES = (
    "incoming",
    "processing",
    "processed",
    "failed",
)

COMMAND_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class ScanCommandError(RuntimeError):
    """Raised when a scanner command cannot be safely published."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mb-scan-command",
        description=(
            "Send a command to a remote ToS scanner command directory "
            "using atomic file publication."
        ),
    )

    parser.add_argument(
        "command",
        choices=sorted(COMMAND_PAYLOADS),
        help="Scanner command to send.",
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
        "--command-id",
        help=(
            "Explicit command ID and filename stem. "
            "A unique ID is generated when omitted."
        ),
    )

    parser.add_argument(
        "--wait",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help=(
            "Wait up to this many seconds for the command to appear "
            "in processed or failed. Default: publish and return immediately."
        ),
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.25,
        metavar="SECONDS",
        help="Polling interval used with --wait. Default: 0.25.",
    )

    return parser


def resolve_command_root(explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        root = explicit_root
    else:
        configured_root = os.environ.get(ENV_SCAN_CONTROL)

        if not configured_root:
            raise ScanCommandError(
                f"No command root supplied. Use --root or set "
                f"{ENV_SCAN_CONTROL}."
            )

        root = Path(os.path.expandvars(configured_root))

    return root.expanduser()


def validate_command_root(root: Path) -> None:
    if not root.exists():
        raise ScanCommandError(f"Command root does not exist: {root}")

    if not root.is_dir():
        raise ScanCommandError(f"Command root is not a directory: {root}")

    missing = [
        directory_name
        for directory_name in REQUIRED_DIRECTORIES
        if not (root / directory_name).is_dir()
    ]

    if missing:
        missing_text = ", ".join(missing)
        raise ScanCommandError(
            f"Command root is missing required directories: {missing_text}"
        )


def generate_command_id(command: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_suffix = uuid.uuid4().hex[:8]

    return f"mb-{command}-{timestamp}-{unique_suffix}"


def validate_command_id(command_id: str) -> None:
    if not command_id:
        raise ScanCommandError("Command ID must not be empty.")

    if not COMMAND_ID_PATTERN.fullmatch(command_id):
        raise ScanCommandError(
            "Command ID may contain only letters, numbers, periods, "
            "underscores, and hyphens."
        )


def publish_command(
    *,
    root: Path,
    command_id: str,
    payload: dict[str, str],
) -> Path:
    """
    Write a complete command as .tmp and atomically rename it to .json.

    The temporary and final files reside in the same directory so the
    rename does not cross filesystems or SMB shares.
    """
    validate_command_root(root)
    validate_command_id(command_id)

    incoming = root / "incoming"
    temporary_path = incoming / f"{command_id}.tmp"
    published_path = incoming / f"{command_id}.json"

    if temporary_path.exists():
        raise ScanCommandError(
            f"Temporary command file already exists: {temporary_path}"
        )

    if published_path.exists():
        raise ScanCommandError(
            f"Published command file already exists: {published_path}"
        )

    try:
        with temporary_path.open(
            "x",
            encoding="utf-8",
            newline="\n",
        ) as output_file:
            json.dump(payload, output_file, indent=2)
            output_file.write("\n")
            output_file.flush()
            os.fsync(output_file.fileno())

        os.replace(temporary_path, published_path)

    except Exception:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise

    return published_path


def find_command_location(
    *,
    root: Path,
    command_id: str,
) -> tuple[str, Path] | None:
    filename = f"{command_id}.json"

    for directory_name in (
        "failed",
        "processed",
        "processing",
        "incoming",
    ):
        candidate = root / directory_name / filename

        if candidate.exists():
            return directory_name, candidate

    return None


def wait_for_result(
    *,
    root: Path,
    command_id: str,
    timeout: float,
    poll_interval: float,
) -> tuple[str, Path] | None:
    deadline = time.monotonic() + timeout

    while True:
        failed_path = root / "failed" / f"{command_id}.json"
        if failed_path.exists():
            return "failed", failed_path

        processed_path = root / "processed" / f"{command_id}.json"
        if processed_path.exists():
            return "processed", processed_path

        if time.monotonic() >= deadline:
            return None

        time.sleep(poll_interval)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.wait < 0:
        parser.error("--wait must be zero or greater.")

    if args.poll_interval <= 0:
        parser.error("--poll-interval must be greater than zero.")

    try:
        root = resolve_command_root(args.root)
        command_id = args.command_id or generate_command_id(args.command)
        payload = dict(COMMAND_PAYLOADS[args.command])

        published_path = publish_command(
            root=root,
            command_id=command_id,
            payload=payload,
        )

        print(f"Command ID : {command_id}")
        print(f"Command    : {args.command}")
        print(f"Published  : {published_path}")

        if args.wait == 0:
            return 0

        result = wait_for_result(
            root=root,
            command_id=command_id,
            timeout=args.wait,
            poll_interval=args.poll_interval,
        )

        if result is None:
            location = find_command_location(
                root=root,
                command_id=command_id,
            )

            print(
                f"Timed out after {args.wait:g} seconds waiting for a result.",
                file=sys.stderr,
            )

            if location is None:
                print(
                    "Current location: command file not found.",
                    file=sys.stderr,
                )
            else:
                directory_name, current_path = location
                print(
                    f"Current location: {directory_name} ({current_path})",
                    file=sys.stderr,
                )

            return 3

        result_name, result_path = result

        print(f"Result     : {result_name}")
        print(f"Result file: {result_path}")

        if result_name == "processed":
            return 0

        return 1

    except (OSError, ScanCommandError) as exc:
        print(f"mb-scan-command: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
