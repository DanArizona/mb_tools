# Changelog

All notable changes to **mb-tools** will be documented in this file.

Versions are tagged in git as `vX.Y.Z` and correspond to the version in `pyproject.toml`.

## [Unreleased]
### Added
-

### Changed
-

### Fixed
-

<br>

## [0.4.0] - YYYY-MM-DD

### Added
- Added encrypted Schwab configuration integration and Schwabdev client creation.
- Added the `mb-schwab-auth` command-line tool.
- Added pseudo-widget models, YAML loading, validation, flattening, and tree reporting.
- Added the `mb-pwidget-tree` command-line tool.
- Added the `mb-env-report` command-line tool.
- Added the `mb-window-survey` command-line tool.
- Added reusable window-discovery and positioning helpers.
- Added window Z-order and overlap diagnostics.
- Added PyYAML as a required dependency.
- Added a 49-test automated regression suite covering configuration, encrypted configuration, pseudo-widgets, CLI entry points, windowing, and Schwab configuration.

### Changed
- Changed configuration precedence to project `.env`, then Windows environment, then packaged defaults.
- Raised the minimum supported Python version to 3.10.
- Expanded installation, configuration, security, testing, and release documentation.

### Removed
- Removed the unused Schwab Qt placeholder module.
- Removed the legacy window-survey implementation.
- Removed unused initial scaffold modules.

### Fixed
- Declared PyYAML so pseudo-widget commands work in clean installations.

## [0.3.0] - 2026-05-06
### Added
- Added `mb_tools.secure_config` for password-based encrypted `.ecfg` configuration files.
- Added support for saving, loading, and reading values from encrypted dictionary-style config files.
- Added Qt password dialogs for opening encrypted config files and setting new passwords.
- Added a Qt `.ecfg` editor with open, save, save-as, row editing, password change, undo/redo, and recent-file support.

### Changed
- Added optional Qt dependency group via `mb_tools[qt]`.

### Notes
- Core encrypted config support does not require PySide6.
- Qt features are imported explicitly from `mb_tools.secure_config.qt_password` and `mb_tools.secure_config.qt_ecfg_editor`.


## [0.2.0] - 2026-05-04
### Added
- Added `logging_queue.py`, a queue-based logging module for threaded applications.
- Added `setup_logging()`, `get_logger()`, `shutdown_logging()`, and `logging_context()` as the public API for queue-based logging.
- Added timestamped log file creation using the current run date/time.
- Added an `ALL` log file that receives records from the main thread and all worker threads.
- Added a `MAIN` log file that receives only records emitted by the main thread.
- Added automatic per-thread log files for non-main worker threads.
- Added optional console echoing of log records.
- Added safe log filename handling for application names and thread names.
- Added a small built-in demo for verifying main-thread and worker-thread logging behavior.

### Changed

- Kept `logging_utils.py` active for compatibility while introducing `logging_queue.py` as the fuller queue-based logging implementation.



## [0.1.0] - 2026-05-03
### Added
- Initial project scaffold with `src/` layout:
  - distribution name: `mb-tools`
  - import package: `mb_tools`
- Version exposed as `mb_tools.__version__` sourced from installed distribution metadata.
- `config.py`:
  - Reads effective Windows environment variables starting with `MB_`.
  - Optional project `.env` parsing with precedence: **Windows env wins over `.env`**.
  - Packaged defaults loaded from `mb_tools/defaults.env` (included as package data) with precedence:
    **Windows env > `.env` > packaged defaults**.
  - Terminal messages for:
    - `.env` vs Windows value differences (Windows wins)
    - keys present only in `.env`
    - defaults used when missing from both Windows and `.env`
    - defaults that differ from already-defined values (keeps earlier value)
  - Flags non-`MB_` keys found in `.env` or defaults as errors (continues).
  - Returns an `MBConfig` object containing `values`, `sources`, and `errors`.
- Module stubs included for future expansion:
  - `helpers.py`, `paths.py`, `credentials.py`, `logging_utils.py`, `logging_queue.py`.

### Changed
-

### Fixed
-