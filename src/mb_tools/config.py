from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import os
import importlib.resources as resources


MB_PREFIX = "MB_"


def _parse_env_text(text: str) -> Dict[str, str]:
    """
    Minimal .env parser:
      - ignores blank lines and lines starting with '#'
      - supports KEY=VALUE (optional leading 'export ')
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

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
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
    sources: Dict[str, str]   # key -> "env" | "dotenv" | "defaults"
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
    Precedence:
      1) Effective Windows env (os.environ) for keys starting with MB_
      2) .env file values (only if key missing from env)
      3) Packaged defaults (only if key missing from env and .env)

    Side effects: NONE (does not modify os.environ). It returns a resolved config object.
    """
    errors: List[str] = []
    values: Dict[str, str] = {}
    sources: Dict[str, str] = {}

    def say(msg: str) -> None:
        if verbose:
            print(msg)

    # 1) Effective Windows env
    env_mb = {k: v for k, v in os.environ.items() if k.startswith(MB_PREFIX)}
    for k, v in env_mb.items():
        values[k] = v
        sources[k] = "env"
    if verbose:
        say(f"[config] Found {len(env_mb)} '{MB_PREFIX}*' variables in Windows env")

    # 2) Project .env
    dotenv_vars: Dict[str, str] = {}
    if dotenv_path is not None:
        dotenv_vars = _load_env_file(dotenv_path)
        if verbose:
            say(f"[config] Read {len(dotenv_vars)} variables from .env: {dotenv_path}")

        for k, v in dotenv_vars.items():
            if not k.startswith(MB_PREFIX):
                errors.append(f".env contains non-{MB_PREFIX} key: {k}")
                say(f"[config][ERROR] .env key does not start with '{MB_PREFIX}': {k}")
                continue

            if k in env_mb:
                if env_mb[k] != v:
                    say(f"[config] .env provides {k} but Windows env wins (values differ)")
                # env already set; keep it
            else:
                # only in .env so far
                values[k] = v
                sources[k] = "dotenv"
                say(f"[config] Using .env value for {k} (not present in Windows env)")

    # 3) Packaged defaults
    if use_packaged_defaults:
        try:
            defaults = _load_packaged_defaults(defaults_filename)
            if verbose:
                say(f"[config] Read {len(defaults)} variables from packaged defaults: {defaults_filename}")
        except FileNotFoundError:
            defaults = {}
            say(f"[config][ERROR] Packaged defaults file not found: {defaults_filename}")
            errors.append(f"Packaged defaults file not found: {defaults_filename}")

        for k, v in defaults.items():
            if not k.startswith(MB_PREFIX):
                errors.append(f"defaults contains non-{MB_PREFIX} key: {k}")
                say(f"[config][ERROR] defaults key does not start with '{MB_PREFIX}': {k}")
                continue

            if k in values:
                if values[k] != v:
                    say(f"[config] Packaged default differs for {k} (keeping {sources[k]} value)")
                continue

            values[k] = v
            sources[k] = "defaults"
            say(f"[config] Using packaged default for {k} (not in env or .env)")

    return MBConfig(values=values, sources=sources, errors=errors)
    