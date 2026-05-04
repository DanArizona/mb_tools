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

---

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