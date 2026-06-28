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

from .client import SchwabdevNotInstalledError, make_secure_schwab_client
from .config import SecureSchwabConfigError


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
        "--timeout",
        type=int,
        default=10,
        help="Schwabdev client timeout in seconds. Default: 10.",
    )

    return parser


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
        client = make_secure_schwab_client(
            ecfg_path,
            password,
            timeout=args.timeout,
        )
    except SchwabdevNotInstalledError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except SecureSchwabConfigError as exc:
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
