# src/mb_tools/env_report.py

"""
Command-line diagnostic report for MB_* environment/config variables.

Shows resolved MB_* values and their sources using mb_tools.config.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mb_tools.config import load_mb_config, print_mb_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report resolved MB_* configuration values and their sources."
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to user/project .env file. Default: .env",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed loading messages.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    env_file = Path(args.env_file) if args.env_file else None

    cfg = load_mb_config(
        dotenv_path=env_file,
        verbose=args.verbose,
    )

    print_mb_config(cfg)

    if cfg.errors:
        print("Errors:")
        for err in cfg.errors:
            print(f"  {err}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
