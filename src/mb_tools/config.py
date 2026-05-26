# src/mb_tools/config.py

"""
mb_tools.config

Configuration loader for MB_* environment variables.

Precedence:
1. Project/specified .env file
2. Windows environment variables
3. Packaged defaults.env file

This module does not modify os.environ.
It reads configuration values and returns an MBConfig object containing
resolved values and source information.

Typical usage:

    from mb_tools.config import load_mb_config

    cfg = load_mb_config(verbose=False)
    scans_dir = cfg.get("MB_SCANS")
    vault_dir = cfg.get_path("MB_VAULT")

Diagnostic usage:

    from mb_tools.config import print_mb_config

    print_mb_config()
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List
import os
import importlib.resources as resources


MB_PREFIX = "MB_"


def _parse_env_text(text: str) -> Dict[str, str]:
    """
    Minimal .env parser:
    - ignores blank lines and lines starting with '#'
    - supports KEY=VALUE
    - supports optional leading 'export '
    - strips surrounding single/double quotes
    """
    out: Dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.lower().startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        if key:
            out[key] = value

    return out


def _load_env_file(path: str | Path) -> Dict[str, str]:
    p = Path(path)

    if not p.exists() or not p.is_file():
        return {}

    return _parse_env_text(p.read_text(encoding="utf-8"))


def _load_packaged_defaults(filename: str = "defaults.env") -> Dict[str, str]:
    """
    Load defaults.env shipped inside the mb_tools package.

    Requires defaults.env to be included as package data.
    """
    data_path = resources.files("mb_tools").joinpath(filename)
    return _parse_env_text(data_path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class MBConfig:
    values: Dict[str, str]
    sources: Dict[str, str]  # key -> "dotenv" | "env" | "defaults"
    errors: List[str]

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.values.get(key, default)

    def get_path(self, key: str, *, must_exist: bool = False) -> Optional[Path]:
        raw = self.values.get(key)

        if raw is None:
            return None

        p = Path(raw)

        if must_exist and not p.exists():
            raise FileNotFoundError(f"{key} resolved to a non-existent path: {p}")

        return p


def load_mb_config(
    *,
    dotenv_path: str | Path | None = ".env",
    use_packaged_defaults: bool = True,
    defaults_filename: str = "defaults.env",
    verbose: bool = True,
) -> MBConfig:
    """
    Load MB_* configuration values.

    Returns:
        MBConfig containing:
            values: resolved key/value pairs
            sources: source for each key: "dotenv", "env", or "defaults"
            errors: non-fatal configuration issues

    Precedence:
        1) Project/specified .env file values
        2) Effective Windows env values from os.environ
        3) Packaged defaults

    Side effects:
        NONE. This function does not modify os.environ.
    """
    errors: List[str] = []
    values: Dict[str, str] = {}
    sources: Dict[str, str] = {}

    def say(msg: str) -> None:
        if verbose:
            print(msg)

    # ------------------------------------------------------------
    # 1) Packaged defaults: lowest priority
    # ------------------------------------------------------------
    defaults: Dict[str, str] = {}

    if use_packaged_defaults:
        try:
            defaults = _load_packaged_defaults(defaults_filename)
            say(
                f"[config] Read {len(defaults)} variables "
                f"from packaged defaults: {defaults_filename}"
            )
        except FileNotFoundError:
            defaults = {}
            msg = f"Packaged defaults file not found: {defaults_filename}"
            errors.append(msg)
            say(f"[config][ERROR] {msg}")

    for k, v in defaults.items():
        if not k.startswith(MB_PREFIX):
            msg = f"defaults contains non-{MB_PREFIX} key: {k}"
            errors.append(msg)
            say(f"[config][ERROR] {msg}")
            continue

        values[k] = v
        sources[k] = "defaults"

    # ------------------------------------------------------------
    # 2) Windows environment: overrides packaged defaults
    # ------------------------------------------------------------
    env_mb = {k: v for k, v in os.environ.items() if k.startswith(MB_PREFIX)}

    say(f"[config] Found {len(env_mb)} '{MB_PREFIX}*' variables in Windows env:")

    for key in sorted(env_mb):
        say(f"[config] {key}")

    for k, v in env_mb.items():
        if k in values and values[k] != v:
            say(f"[config] Windows env overrides packaged default for {k}")

        values[k] = v
        sources[k] = "env"

    # ------------------------------------------------------------
    # 3) Project/specified .env: highest priority
    # ------------------------------------------------------------
    dotenv_vars: Dict[str, str] = {}

    if dotenv_path is not None:
        dotenv_vars = _load_env_file(dotenv_path)
        say(f"[config] Read {len(dotenv_vars)} variables from .env: {dotenv_path}")

    for k, v in dotenv_vars.items():
        if not k.startswith(MB_PREFIX):
            msg = f".env contains non-{MB_PREFIX} key: {k}"
            errors.append(msg)
            say(f"[config][ERROR] {msg}")
            continue

        if k in values and values[k] != v:
            say(f"[config] Project .env overrides {sources[k]} value for {k}")
        elif k not in values:
            say(f"[config] Using project .env value for {k}")

        values[k] = v
        sources[k] = "dotenv"

    return MBConfig(values=values, sources=sources, errors=errors)


def print_mb_config(config: MBConfig | None = None) -> None:
    """
    Diagnostic helper: print resolved MB_* values and their sources.
    """
    if config is None:
        config = load_mb_config(verbose=False)

    source_labels = {
        "dotenv": "project .env",
        "env": "Windows environment",
        "defaults": "package defaults.env",
    }

    for key in sorted(config.values):
        source = source_labels.get(config.sources.get(key, "unknown"), "unknown")
        print(key)
        print(f" value : {config.values[key]}")
        print(f" source: {source}")
        print()


def main() -> None:
    """
    Command-line diagnostic entry point.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Show resolved MB_* configuration values and their sources."
    )

    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to project .env file. Default: .env",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed loading messages.",
    )

    args = parser.parse_args()

    cfg = load_mb_config(dotenv_path=args.env_file, verbose=args.verbose)
    print_mb_config(cfg)

    if cfg.errors:
        print("Errors:")
        for err in cfg.errors:
            print(f"  {err}")


if __name__ == "__main__":
    main()
