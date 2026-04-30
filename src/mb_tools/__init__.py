from importlib.metadata import version as _dist_version

__version__ = _dist_version("mb-tools")  # distribution name from pyproject.toml

# export your public API
from .config import MBConfig, load_mb_config

__all__ = ["MBConfig", "load_mb_config", "__version__"]
