"""
Command-line Schwab authorization / token refresh helper.

This command loads a secure Schwab .ecfg file, creates a Schwabdev client,
and lets Schwabdev refresh existing tokens or run the browser authorization
flow when needed.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path
from typing import Sequence

from .client import (
    SchwabdevNotInstalledError,
    SchwabdevVersionError,
    make_secure_schwab_client,
)
from .config import SecureSchwabConfigError, load_secure_schwab_config
from .status import SchwabTokenStatusError, read_schwab_token_status


DEFAULT_ECFG_NAME = "secure_schwabdev.ecfg"


def default_ecfg_path() -> Path:
    """
    Resolve the default Schwab .ecfg path.

    Preference:
        1. MB_SCHWAB_ECFG
        2. MB_VAULT / secure_schwabdev.ecfg
        3. ./secure_schwabdev.ecfg
    """

    schwab_ecfg = os.environ.get("MB_SCHWAB_ECFG")
    if schwab_ecfg:
        return Path(schwab_ecfg).expanduser()

    vault = os.environ.get("MB_VAULT")
    if vault:
        return Path(vault).expanduser() / DEFAULT_ECFG_NAME

    return Path(DEFAULT_ECFG_NAME)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Authorize or refresh Schwabdev tokens using an encrypted Schwab .ecfg file."
        )
    )

    parser.add_argument(
        "--ecfg",
        type=Path,
        default=None,
        help=(
            "Path to secure Schwab .ecfg file. "
            "Defaults to MB_SCHWAB_ECFG, then MB_VAULT\\secure_schwabdev.ecfg, "
            "then .\\secure_schwabdev.ecfg."
        ),
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help=(
            "Show access/refresh token lifetimes without refreshing tokens "
            "or opening a browser."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Schwabdev client timeout in seconds. Default: 10.",
    )

    return parser


def _remaining_text(seconds: float) -> str:
    expired = seconds < 0
    total = abs(int(seconds))
    days, remainder = divmod(total, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, secs = divmod(remainder, 60)
    pieces = []
    if days:
        pieces.append(f"{days}d")
    if hours or days:
        pieces.append(f"{hours}h")
    pieces.append(f"{minutes}m")
    pieces.append(f"{secs}s")
    value = " ".join(pieces)
    return f"EXPIRED by {value}" if expired else value


def _print_status(ecfg_path: Path, password: str) -> int:
    config = load_secure_schwab_config(ecfg_path, password)
    status = read_schwab_token_status(config)

    print()
    print("Schwab token status (read-only)")
    print("=" * 79)
    print(f"Token database       : {status.tokens_db}")
    print(f"Observed UTC         : {status.observed_at.isoformat()}")
    print(
        "Access expires UTC  : "
        f"{status.access_token_expires_at.isoformat()}"
    )
    print(
        "Access remaining    : "
        f"{_remaining_text(status.access_remaining.total_seconds())}"
    )
    print(
        "Refresh expires UTC : "
        f"{status.refresh_token_expires_at.isoformat()}"
    )
    print(
        "Refresh remaining   : "
        f"{_remaining_text(status.refresh_remaining.total_seconds())}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ecfg_path = (args.ecfg or default_ecfg_path()).expanduser()

    print(f"Schwab .ecfg: {ecfg_path}")

    if not ecfg_path.exists():
        print(f"ERROR: Schwab .ecfg file does not exist: {ecfg_path}", file=sys.stderr)
        return 2

    password = getpass.getpass("ecfg password: ")

    try:
        if args.status:
            return _print_status(ecfg_path, password)
        client = make_secure_schwab_client(
            ecfg_path,
            password,
            timeout=args.timeout,
        )
    except SchwabdevNotInstalledError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except SchwabdevVersionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except (SecureSchwabConfigError, SchwabTokenStatusError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"ERROR: Schwab authorization/refresh failed: {exc}", file=sys.stderr)
        return 1

    print()
    print("Schwab client created successfully.")
    print(f"Client type: {type(client).__name__}")
    print("If Schwabdev required authorization, the token database should now be updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
