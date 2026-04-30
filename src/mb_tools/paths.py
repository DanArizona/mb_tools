from pathlib import Path

def as_path(p: str | Path) -> Path:
    return p if isinstance(p, Path) else Path(p)
