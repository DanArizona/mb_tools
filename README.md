# mb_tools

Private Python utility package for the MasterBot project and related `MB_*` tooling.

The package provides:

* Configuration loading and diagnostics for `MB_*` variables
* Pseudo-widget YAML loading, validation, and reporting
* Windows window-discovery and positioning helpers
* Window survey and Z-order diagnostics
* Encrypted configuration support
* Schwab authorization and token-refresh support

## Package names

The package uses two related names:

* Distribution name used by pip: `mb-tools`
* Import package used by Python: `mb_tools`

Example:

```python
import mb_tools

print(mb_tools.__version__)
```

## Requirements

* Python 3.10 or later
* Windows for the window-survey and GUI-window utilities
* Git when installing directly from GitHub

Python 3.12 is the primary development version.

## Installation

### Install stable release `v0.4.0`

Activate the desired Conda environment first:

```cmd
conda activate sea-green
```

Install the stable release directly from its Git tag:

```cmd
python -m pip install "git+https://github.com/DanArizona/mb_tools.git@v0.4.0"
```

Do not use `--user` when installing into an active Conda environment.

### Install with Schwab support

```cmd
python -m pip install "mb-tools[schwab] @ git+https://github.com/DanArizona/mb_tools.git@v0.4.0"
```

### Install with Qt support

```cmd
python -m pip install "mb-tools[qt] @ git+https://github.com/DanArizona/mb_tools.git@v0.4.0"
```

### Install with both optional feature groups

```cmd
python -m pip install "mb-tools[qt,schwab] @ git+https://github.com/DanArizona/mb_tools.git@v0.4.0"
```

### Verify the installation

```cmd
python -m pip show mb-tools
python -c "import mb_tools; print(mb_tools.__version__); print(mb_tools.__file__)"
```

Expected version:

```text
0.4.0
```

## Development installation

Clone the repository:

```cmd
git clone https://github.com/DanArizona/mb_tools.git
cd mb_tools
```

Install the active checkout in editable mode:

```cmd
python -m pip install -e ".[qt,schwab]"
```

An editable installation uses the source files in the local repository. Switching Git branches therefore changes the Python source being imported.

After changing packaging metadata such as `pyproject.toml`, dependencies, package data, entry points, or the version, rerun:

```cmd
python -m pip install -e ".[qt,schwab]"
```

## Configuration

`mb_tools.config` resolves configuration variables whose names begin with `MB_`.

### Precedence

Configuration values are resolved in this order:

1. Project or explicitly selected `.env` file
2. Effective Windows environment variables
3. Packaged `defaults.env`

The `.env` value wins when the same variable is defined in both `.env` and the Windows environment.

The configuration loader does not modify `os.environ`. It returns an `MBConfig` object containing:

* `values`: resolved configuration values
* `sources`: source selected for each value
* `errors`: nonfatal configuration problems

### Python example

```python
from mb_tools.config import load_mb_config

config = load_mb_config(
    dotenv_path=".env",
    verbose=False,
)

scans_dir = config.get_path("MB_SCANS")
vault_dir = config.get_path("MB_VAULT")

print("MB_SCANS:", scans_dir)
print("MB_VAULT:", vault_dir)
print("MB_SCANS source:", config.sources.get("MB_SCANS"))

if config.errors:
    for error in config.errors:
        print("Configuration error:", error)
```

### Example `.env`

```dotenv
MB_SCANS=C:\Users\DanLa\Documents\github\stockScans
MB_VAULT=\\MasterBot\MB_vault_Arjan
MB_LOG_FOLDER=.\logs
```

Do not store passwords, API secrets, or tokens in a committed `.env` file.

## Command-line tools

### `mb-env-report`

Reports resolved `MB_*` values and the source selected for each value.

Use the `.env` file in the current directory:

```cmd
mb-env-report
```

Use a specific `.env` file:

```cmd
mb-env-report --env-file "C:\path\to\project\.env"
```

Show detailed configuration-loading messages:

```cmd
mb-env-report --verbose --env-file "C:\path\to\project\.env"
```

Show command help:

```cmd
mb-env-report --help
```

### `mb-window-survey`

Surveys open Windows application windows and reports their titles, coordinates, dimensions, native window handles, foreground state, topmost state, Z-order, and possible overlap by windows in front of them.

Survey visible windows:

```cmd
mb-window-survey
```

Show only titles containing a specified string:

```cmd
mb-window-survey --contains thinkorswim
```

Sort windows from front to back by Z-order:

```cmd
mb-window-survey --z-order
```

Include minimized or zero-size windows when reported by Windows:

```cmd
mb-window-survey --all
```

Combine options:

```cmd
mb-window-survey --contains thinkorswim --z-order
```

Show command help:

```cmd
mb-window-survey --help
```

### `mb-pwidget-tree`

Loads a pseudo-widget YAML layout and prints its widget hierarchy.

Print all widget roots and descendants:

```cmd
mb-pwidget-tree "C:\path\to\layout.yaml"
```

Print only one top-level root:

```cmd
mb-pwidget-tree "C:\path\to\layout.yaml" --root win_main
```

List only the names of top-level roots:

```cmd
mb-pwidget-tree "C:\path\to\layout.yaml" --roots-only
```

Suppress absolute coordinates and text labels:

```cmd
mb-pwidget-tree "C:\path\to\layout.yaml" --no-abs --no-text
```

Show command help:

```cmd
mb-pwidget-tree --help
```

### `mb-schwab-auth`

Creates a Schwabdev client from an encrypted Schwab `.ecfg` file. Schwabdev can then refresh existing tokens or start its browser-based authorization flow when authorization is required.

Install Schwab support before using this command:

```cmd
python -m pip install "mb-tools[schwab] @ git+https://github.com/DanArizona/mb_tools.git@v0.4.0"
```

Show command help:

```cmd
mb-schwab-auth --help
```

Use the default encrypted configuration path:

```cmd
mb-schwab-auth
```

Specify the encrypted configuration explicitly:

```cmd
mb-schwab-auth --ecfg "C:\path\to\secure_schwabdev.ecfg"
```

Specify a client timeout:

```cmd
mb-schwab-auth --ecfg "C:\path\to\secure_schwabdev.ecfg" --timeout 20
```

The default `.ecfg` path is selected in this order:

1. `MB_SCHWAB_ECFG`
2. `MB_VAULT\secure_schwabdev.ecfg`
3. `.\secure_schwabdev.ecfg`

The command prompts for the encrypted-configuration password without displaying it on the terminal.

## Reusable window helpers

The `mb_tools.windowing` module provides reusable helpers for locating and controlling windows by stable title prefix.

```python
from mb_tools.windowing import (
    bring_window_to_front_by_prefix,
    find_window_by_title_prefix,
    is_window_visible_by_prefix,
)

title_prefix = "Main@thinkorswim"

window = find_window_by_title_prefix(title_prefix)

if window is None:
    print("Window not found")
else:
    print("Matched:", window.title)

if is_window_visible_by_prefix(title_prefix):
    bring_window_to_front_by_prefix(title_prefix)
```

Prefix matching supports application titles whose suffix changes, such as a build number or document name.

## Pseudo-widget loading

Pseudo-widget layout files can also be loaded from Python:

```python
from pathlib import Path

from mb_tools.pseudo_widgets.yaml_loader import load_widget_stacks

layout_path = Path(r"C:\path\to\layout.yaml")
widget_stacks = load_widget_stacks(layout_path)

for root_name in widget_stacks:
    print(root_name)
```

## Security

Never commit any of the following:

* `.env` files containing private values
* `.ecfg` encrypted-configuration files
* Schwab token databases
* API keys or application secrets
* Passwords
* Locally generated credentials
* Private certificate or key files

Even encrypted files should normally remain outside the repository unless there is a deliberate reason to version them.

Before publishing or tagging a release, review both the working tree and Git history for accidentally committed credentials.

## Building a release

Install the build tools:

```cmd
python -m pip install --upgrade build twine
```

Remove old artifacts:

```cmd
rmdir /s /q build
rmdir /s /q dist
```

Build the wheel and source archive:

```cmd
python -m build
```

Validate the generated distributions:

```cmd
python -m twine check dist\*
```

Inspect the wheel contents:

```cmd
python -m zipfile -l dist\mb_tools-0.4.0-py3-none-any.whl
```

## Git versioning model

`main` is the active development line.

Stable releases are preserved using annotated Git tags:

```text
v0.1.0
v0.2.0
v0.3.0
v0.4.0
```

Install a stable version by naming its tag explicitly:

```cmd
python -m pip install "git+https://github.com/DanArizona/mb_tools.git@v0.4.0"
```

Do not move or replace a published release tag.

## License

Proprietary. For private use by the project owner.
