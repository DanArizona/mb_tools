# mb_tools

Private Python utility package for the MasterBot project and related `MB_*` tooling.

The package provides:

* Configuration loading and diagnostics for `MB_*` variables
* Pseudo-widget YAML loading, validation, and reporting
* Windows window-discovery and positioning helpers
* Window survey and Z-order diagnostics
* Encrypted configuration support
* A Qt encrypted-configuration editor
* Schwab authorization and token-refresh support
* Remote scanner command publication
* Scanner heartbeat status reporting

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

### Install stable release `v0.6.0`

Activate the desired Conda environment first:

```cmd
conda activate sea-green
```

Install the stable release directly from its Git tag:

```cmd
python -m pip install "git+https://github.com/DanArizona/mb_tools.git@v0.6.0"
```

Do not use `--user` when installing into an active Conda environment.

### Install with Schwab support

```cmd
python -m pip install "mb-tools[schwab] @ git+https://github.com/DanArizona/mb_tools.git@v0.6.0"
```

### Install with Qt support

```cmd
python -m pip install "mb-tools[qt] @ git+https://github.com/DanArizona/mb_tools.git@v0.6.0"
```

### Install with both optional feature groups

```cmd
python -m pip install "mb-tools[qt,schwab] @ git+https://github.com/DanArizona/mb_tools.git@v0.6.0"
```

### Install from the active `main` branch

The `main` branch is the active development line and may contain changes newer than the latest stable release.

For reproducible installations, prefer a tagged stable release.

Install or refresh `mb_tools` from `main` without reinstalling dependencies:

```cmd
python -m pip install --force-reinstall --no-deps "git+https://github.com/DanArizona/mb_tools.git@main"
```

### Verify the installation

```cmd
python -m pip show mb-tools
python -c "import mb_tools; print(mb_tools.__version__); print(mb_tools.__file__)"
```

For stable release `v0.6.0`, the expected version is:

```text
0.6.0
```

## Development installation

Clone the repository:

```cmd
git clone https://github.com/DanArizona/mb_tools.git
cd mb_tools
```

Install the active checkout in editable mode:

```cmd
python -m pip install -e ".[qt,schwab,test]"
```

An editable installation uses the source files in the local repository. Switching Git branches therefore changes the Python source being imported.

After changing packaging metadata such as `pyproject.toml`, dependencies, package data, entry points, or the version, rerun:

```cmd
python -m pip install -e ".[qt,schwab,test]"
```

Run the complete test suite:

```cmd
python -m pytest -q
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
MB_SCANS=C:\MB\scans
MB_VAULT=\\SERVER\MB_vault
MB_LOG_FOLDER=.\logs
```

Do not store passwords, API secrets, or tokens in a committed `.env` file.

## Scanner command-root configuration

The scanner command tools use:

```text
MB_SCAN_CONTROL
```

This value identifies the shared root directory used to exchange scanner commands and heartbeat status.

Example on MasterBot:

```cmd
set MB_SCAN_CONTROL=\\El-Cheapo\SCANCTRL
```

To save the value persistently for future CMD sessions:

```cmd
setx MB_SCAN_CONTROL "\\El-Cheapo\SCANCTRL"
```

Open a new terminal after using `setx`. The current CMD process does not automatically receive the newly stored persistent value.

The scanner command tools resolve the command root in this order:

1. Explicit `--root`
2. `MB_SCAN_CONTROL` from the current process environment

These commands read `MB_SCAN_CONTROL` directly from `os.environ`. They do not automatically load it from a project `.env` file.

A typical scanner command root contains:

```text
incoming\
processing\
processed\
failed\
status\
    scanner_heartbeat.json
```

Example remote command root:

```text
\\El-Cheapo\SCANCTRL
```

Example corresponding local directory on El-Cheapo:

```text
C:\Users\DanLa\Documents\github\stockScans_control
```

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

### `mb-scan-command`

`mb-scan-command` publishes a JSON command to a local or remote ToS scanner command directory.

This command is included in `v0.5.0` and later.

Show help:

```cmd
mb-scan-command --help
```

#### Supported commands

| Command              | Purpose                                          |
| -------------------- | ------------------------------------------------ |
| `start`              | Mark the scanner as running                      |
| `stop`               | Request scanner command-loop shutdown            |
| `pause`              | Pause scanner runtime operation                  |
| `resume`             | Resume scanner runtime operation                 |
| `export_wl`          | Export the current ThinkOrSwim Watchlist         |
| `suspend_exports`    | Suspend scheduled scanner and Watchlist exports  |
| `resume_exports`     | Resume scheduled scanner and Watchlist exports   |
| `replace_wl_symbols` | Replace the personal `Default` Watchlist symbols |
| `add_wl_symbols`     | Add symbols to the personal `Default` Watchlist  |

Basic examples:

```cmd
mb-scan-command start
mb-scan-command pause
mb-scan-command resume
mb-scan-command export_wl
mb-scan-command suspend_exports
mb-scan-command resume_exports
mb-scan-command stop
```

#### Coordinating Watchlist updates with scheduled exports

`pause` and `suspend_exports` serve different purposes.

`pause` pauses scanner runtime operation. `suspend_exports` leaves the scanner operational while preventing scheduled exports from starting. This allows a Watchlist update to be performed without colliding with a timed ThinkOrSwim export.

The normal coordination sequence is:

```cmd
mb-scan-command suspend_exports --wait 10
mb-scan-command replace_wl_symbols --symbols AAPL MSFT NVDA --wait 10
mb-scan-command resume_exports --wait 10
```

While exports are suspended, Watchlist symbol updates remain permitted, but scheduled exports and explicit export requests are prevented from starting.

The `suspend_exports` and `resume_exports` commands are included in `v0.6.0` and later.

Use an explicit command root:

```cmd
mb-scan-command start --root "\\El-Cheapo\SCANCTRL"
```

Wait up to ten seconds for ingress processing:

```cmd
mb-scan-command start --wait 10
```

Use both options:

```cmd
mb-scan-command start --root "\\El-Cheapo\SCANCTRL" --wait 10
```

#### Watchlist symbol commands

Replace the Default Watchlist:

```cmd
mb-scan-command replace_wl_symbols --symbols AAPL MSFT NVDA --wait 10
```

Add symbols to the Default Watchlist:

```cmd
mb-scan-command add_wl_symbols --symbols AMD ORCL IBM --wait 10
```

Comma-separated values are also accepted:

```cmd
mb-scan-command add_wl_symbols --symbols AMD,ORCL,IBM --wait 10
```

Multiple arguments may combine spaces and commas:

```cmd
mb-scan-command replace_wl_symbols --symbols AAPL,MSFT NVDA AAPL --wait 10
```

Symbols are:

* converted to uppercase;
* split on spaces and commas;
* de-duplicated;
* retained in first-seen order.

The preceding example publishes:

```json
{
  "command": "replace_wl_symbols",
  "symbols": [
    "AAPL",
    "MSFT",
    "NVDA"
  ]
}
```

The `--symbols` option is valid only with:

```text
replace_wl_symbols
add_wl_symbols
```

#### Atomic command publication

A command is first written as a temporary file in the `incoming` directory and then atomically renamed to its final `.json` filename.

This prevents the remote scanner from reading a partially written command.

#### `--wait` behavior

Without `--wait`, the command returns after publishing the JSON file.

With `--wait`, it waits for the command file to appear in either:

```text
processed\
failed\
```

Example:

```cmd
mb-scan-command export_wl --wait 10
```

Typical result:

```text
Command ID : mb-export_wl-20260726-042302-8367318b
Command    : export_wl
Published  : \\El-Cheapo\SCANCTRL\incoming\mb-export_wl-20260726-042302-8367318b.json
Result     : processed
Result file: \\El-Cheapo\SCANCTRL\processed\mb-export_wl-20260726-042302-8367318b.json
```

A `processed` result means the scanner accepted the command and submitted it to its job queue.

It does not necessarily prove that a longer ThinkOrSwim GUI action has already finished. Use `mb-scan-status` to inspect the current job, scanner state, and most recent result.

#### Explicit command IDs

Normally, `mb-scan-command` generates a unique command ID.

An explicit ID can be supplied for testing:

```cmd
mb-scan-command start --command-id test-start-0001
```

Command IDs may contain only:

```text
letters
numbers
periods
underscores
hyphens
```

#### Poll interval

The default polling interval used with `--wait` is 0.25 seconds.

It can be changed with:

```cmd
mb-scan-command start --wait 10 --poll-interval 0.5
```

#### `mb-scan-command` exit codes

| Code | Meaning                                                 |
| ---: | ------------------------------------------------------- |
|  `0` | Command published, or reached `processed` while waiting |
|  `1` | Command reached `failed`                                |
|  `2` | Configuration, validation, or filesystem error          |
|  `3` | Timed out waiting for `processed` or `failed`           |

### `mb-scan-status`

`mb-scan-status` reads and interprets the scanner heartbeat:

```text
<command-root>\status\scanner_heartbeat.json
```

This command is included in `v0.5.0` and later.

Beginning with `v0.6.0`, the status output also reports whether scheduled exports are suspended.

For example:

```text
Scanner status : HEALTHY
Detail         : Scanner heartbeat is current; exports are suspended.
Loop state     : exports_suspended
Running        : yes
Paused         : no
Exports suspended: yes
```

`exports_suspended` is a healthy operational loop state when the heartbeat is current. It indicates that scheduled exports are deliberately suspended; it does not mean that the scanner command loop has failed.

Basic use:

```cmd
mb-scan-status
```

Use an explicit root:

```cmd
mb-scan-status --root "\\El-Cheapo\SCANCTRL"
```

Show help:

```cmd
mb-scan-status --help
```

#### Stale threshold

The default stale-heartbeat threshold is 30 seconds.

Change it with:

```cmd
mb-scan-status --stale-after 60
```

#### JSON output

Print machine-readable JSON:

```cmd
mb-scan-status --json
```

Example:

```json
{
  "age_seconds": 1.2,
  "detail": "Scanner heartbeat is current.",
  "heartbeat": {
    "application": "ToS_scanner",
    "current_job": null,
    "heartbeat_at_utc": "2026-07-26T09:23:04Z",
    "heartbeat_interval_s": 5.0,
    "heartbeat_sequence": 259,
    "host": "El-Cheapo",
    "last_job": {
      "command_id": "mb-start-example",
      "error": null,
      "kind": "start",
      "message": "Scanner marked running.",
      "ok": true
    },
    "loop_state": "idle",
    "paused": false,
    "pid": 24168,
    "running": true,
    "schema_version": 1,
    "shutdown_requested": false,
    "started_at_utc": "2026-07-26T09:00:00Z"
  },
  "heartbeat_path": "\\\\El-Cheapo\\SCANCTRL\\status\\scanner_heartbeat.json",
  "status": "HEALTHY"
}
```

#### Human-readable output

Example healthy result:

```text
Scanner status : HEALTHY
Detail         : Scanner heartbeat is current.
Heartbeat file : \\El-Cheapo\SCANCTRL\status\scanner_heartbeat.json
Heartbeat age  : 1.2 seconds
Host           : El-Cheapo
Loop state     : idle
Running        : yes
Paused         : no
Sequence       : 259
PID            : 24168
Last command   : start
Last result    : Scanner marked running.
```

Example paused result:

```text
Scanner status : PAUSED
Detail         : Scanner heartbeat is current and paused.
Heartbeat file : \\El-Cheapo\SCANCTRL\status\scanner_heartbeat.json
Heartbeat age  : 2.2 seconds
Host           : El-Cheapo
Loop state     : paused
Running        : yes
Paused         : yes
Sequence       : 267
PID            : 24168
Last command   : pause
Last result    : Scanner paused.
```

Example stopped result:

```text
Scanner status : STOPPED
Detail         : Scanner published a stopped state.
Heartbeat file : \\El-Cheapo\SCANCTRL\status\scanner_heartbeat.json
Heartbeat age  : 4.4 seconds
Host           : El-Cheapo
Loop state     : stopped
Running        : no
Paused         : no
Sequence       : 278
PID            : 24168
Last command   : stop
Last result    : Scanner stop requested.
```

#### Scanner status classifications

| Status        | Meaning                                                      |
| ------------- | ------------------------------------------------------------ |
| `HEALTHY`     | Heartbeat is current and loop state is idle                  |
| `PAUSED`      | Heartbeat is current and scanner is paused                   |
| `BUSY`        | Heartbeat is current and a job is being processed            |
| `WAITING`     | Scanner is waiting for operator confirmation                 |
| `STOPPED`     | Scanner explicitly published a stopped state                 |
| `STALE`       | A non-stopped heartbeat is older than the stale threshold    |
| `MISSING`     | Command root is accessible but no heartbeat file exists      |
| `INVALID`     | Heartbeat file is malformed or has an invalid timestamp      |
| `UNREACHABLE` | Command root or heartbeat file cannot be accessed            |
| `UNKNOWN`     | Heartbeat is current but contains an unrecognized loop state |

An explicitly stopped heartbeat remains `STOPPED` even after its timestamp becomes old. This distinguishes a clean shutdown from a scanner process that disappeared unexpectedly.

`HEALTHY` describes the command loop, not necessarily the scanner's `running` flag.

For example:

```text
Scanner status : HEALTHY
Loop state     : idle
Running        : no
```

means the command loop is alive and responsive, but no `start` command has marked the scanner as running.

#### `mb-scan-status` exit codes

| Code | Meaning                                                                                              |
| ---: | ---------------------------------------------------------------------------------------------------- |
|  `0` | Operational status: `HEALTHY`, `PAUSED`, `BUSY`, or `WAITING`                                        |
|  `1` | Non-operational status such as `STOPPED`, `STALE`, `MISSING`, `INVALID`, `UNREACHABLE`, or `UNKNOWN` |
|  `2` | Command-line or root-configuration error                                                             |

Check the exit code from CMD:

```cmd
mb-scan-status
echo Exit code: %ERRORLEVEL%
```

### Typical MasterBot scanner workflow

Check the command loop:

```cmd
mb-scan-status
```

Start scanner operation:

```cmd
mb-scan-command start --wait 10
mb-scan-status
```

Export the Watchlist:

```cmd
mb-scan-command export_wl --wait 10
mb-scan-status
```

Pause operation:

```cmd
mb-scan-command pause --wait 10
mb-scan-status
```

Resume operation:

```cmd
mb-scan-command resume --wait 10
mb-scan-status
```

Replace the Default Watchlist:

```cmd
mb-scan-command replace_wl_symbols --symbols AAPL MSFT NVDA --wait 10
mb-scan-status
```

Add symbols to the Default Watchlist:

```cmd
mb-scan-command add_wl_symbols --symbols AMD ORCL --wait 10
mb-scan-status
```

Stop the command loop:

```cmd
mb-scan-command stop --wait 10
mb-scan-status
```

A stopped scanner status intentionally returns exit code `1`.

### Qt encrypted-configuration editor

`mb_tools` includes a standalone Qt editor for creating and modifying encrypted `.ecfg` configuration files.

Install Qt support first:

```cmd
python -m pip install "mb-tools[qt] @ git+https://github.com/DanArizona/mb_tools.git@v0.6.0"
```

For an editable development installation:

```cmd
python -m pip install -e ".[qt]"
```

Launch the editor with:

```cmd
python -m mb_tools.secure_config.qt_ecfg_editor
```

The editor can be used to:

* open an existing encrypted `.ecfg` file;
* create a new encrypted configuration;
* add, edit, or remove configuration values;
* save the encrypted file using a password.

Encrypted configuration files may contain credentials or other sensitive configuration values. Store them outside the repository unless there is a deliberate reason to version them.

Do not forget the password used to encrypt an `.ecfg` file. The encrypted contents cannot be recovered without the correct password.

### `mb-schwab-auth`

Creates a Schwabdev client from an encrypted Schwab `.ecfg` file.

Schwabdev can then:

* use an existing token database;
* refresh tokens when possible;
* start its browser-based authorization flow when authorization is required.

Install Schwab support before using this command:

```cmd
python -m pip install "mb-tools[schwab] @ git+https://github.com/DanArizona/mb_tools.git@v0.6.0"
```

To install Schwab support from the active `main` branch instead:

```cmd
python -m pip install "mb-tools[schwab] @ git+https://github.com/DanArizona/mb_tools.git@main"
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

A typical Schwab encrypted configuration contains values required by the local Schwabdev client, such as application credentials and callback configuration. Keep the exact field names consistent with the version of the Schwab configuration loader in use.

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

Inspect generated files:

```cmd
dir dist
```

Inspect a wheel:

```cmd
python -m zipfile -l dist\<wheel-filename>.whl
```

## Git versioning model

`main` is the active development line.

Stable releases are preserved using annotated Git tags:

```text
v0.1.0
v0.2.0
v0.3.0
v0.4.0
v0.5.0
v0.6.0
```

Install a stable version by naming its tag explicitly:

```cmd
python -m pip install "git+https://github.com/DanArizona/mb_tools.git@v0.6.0"
```

Install the latest active development version from `main`:

```cmd
python -m pip install --force-reinstall --no-deps "git+https://github.com/DanArizona/mb_tools.git@main"
```

Do not move or replace a published release tag.

## License

Proprietary. For private use by the project owner.
