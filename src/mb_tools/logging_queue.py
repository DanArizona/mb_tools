"""
logging_queue.py

Queue-based logging setup for applications that may use worker threads.

Creates:
    1. ALL log file:
       receives records from all threads.

    2. MAIN-only log file:
       receives only records emitted by the main thread.

    3. Per-thread log files:
       receives records for each non-main thread, one file per thread.

Typical usage:

    from mb_tools.logging_queue import setup_logging, get_logger, shutdown_logging

    log_mgr = setup_logging(log_dir="logs", app_name="survey")

    logger = get_logger(__name__)
    logger.info("Program started")

    # ... run program ...

    shutdown_logging()

You may also use it as a context manager:

    from mb_tools.logging_queue import logging_context, get_logger

    with logging_context(log_dir="logs", app_name="survey"):
        logger = get_logger(__name__)
        logger.info("Program started")
"""

from __future__ import annotations

import atexit
import logging
import logging.handlers
import queue
import re
import sys
import threading

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_ACTIVE_MANAGER: Optional["LoggingQueueManager"] = None


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def _safe_filename_part(value: str) -> str:
    """
    Convert an arbitrary string into a safe filename component.

    Examples:
        "Thread-1 (worker)" -> "Thread-1_worker"
        "my/logger:name"    -> "my_logger_name"
    """
    value = value.strip()
    value = re.sub(r"[^\w.\-]+", "_", value)
    value = value.strip("._")
    return value or "unnamed"


def make_run_timestamp() -> str:
    """
    Return a timestamp suitable for log filenames.

    Example:
        2026-05-03_18-42-11
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

class MainThreadOnlyFilter(logging.Filter):
    """
    Allow only records emitted from the original main thread.
    """

    def __init__(self, main_thread_id: int):
        super().__init__()
        self.main_thread_id = main_thread_id

    def filter(self, record: logging.LogRecord) -> bool:
        return record.thread == self.main_thread_id


class NonMainThreadOnlyFilter(logging.Filter):
    """
    Allow only records emitted outside the original main thread.
    """

    def __init__(self, main_thread_id: int):
        super().__init__()
        self.main_thread_id = main_thread_id

    def filter(self, record: logging.LogRecord) -> bool:
        return record.thread != self.main_thread_id


# ---------------------------------------------------------------------------
# Dynamic per-thread file handler
# ---------------------------------------------------------------------------

class PerThreadFileHandler(logging.Handler):
    """
    Logging handler that writes each non-main thread's records to its own file.

    Files are created lazily. If a worker thread never logs anything, no file
    is created for it.

    Example generated filename:

        survey 2026-05-03_18-42-11 thread Worker-1.log
    """

    def __init__(
        self,
        log_dir: Path,
        app_name: str,
        run_timestamp: str,
        main_thread_id: int,
        *,
        encoding: str = "utf-8",
    ):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.app_name = _safe_filename_part(app_name)
        self.run_timestamp = run_timestamp
        self.main_thread_id = main_thread_id
        self.encoding = encoding

        self._handlers: dict[int, logging.FileHandler] = {}
        self._lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        """
        Route the record to the file handler for its thread.
        """
        if record.thread == self.main_thread_id:
            return

        try:
            handler = self._get_handler_for_record(record)
            handler.emit(record)
        except Exception:
            self.handleError(record)

    def _get_handler_for_record(self, record: logging.LogRecord) -> logging.FileHandler:
        """
        Return an existing per-thread handler or create a new one.
        """
        thread_id = record.thread

        with self._lock:
            existing = self._handlers.get(thread_id)
            if existing is not None:
                return existing

            thread_name = _safe_filename_part(record.threadName)
            filename = (
                f"{self.app_name} "
                f"{self.run_timestamp} "
                f"thread {thread_name}.log"
            )

            path = self.log_dir / filename

            handler = logging.FileHandler(
                path,
                mode="a",
                encoding=self.encoding,
            )

            handler.setLevel(self.level)
            handler.setFormatter(self.formatter)

            self._handlers[thread_id] = handler
            return handler

    def flush(self) -> None:
        with self._lock:
            for handler in self._handlers.values():
                handler.flush()

    def close(self) -> None:
        with self._lock:
            for handler in self._handlers.values():
                handler.close()
            self._handlers.clear()

        super().close()


# ---------------------------------------------------------------------------
# Logging manager
# ---------------------------------------------------------------------------

@dataclass
class LoggingQueueManager:
    """
    Owns the queue, queue listener, handlers, and setup metadata.
    """

    log_dir: Path
    app_name: str
    run_timestamp: str
    main_thread_id: int
    log_queue: queue.Queue
    queue_listener: logging.handlers.QueueListener

    all_log_path: Path
    main_log_path: Path

    started: bool = False
    previous_root_handlers: Optional[list[logging.Handler]] = None
    previous_root_level: Optional[int] = None

    def start(self) -> None:
        if not self.started:
            self.queue_listener.start()
            self.started = True

    def shutdown(self) -> None:
        """
        Stop the listener and flush/close listener-side handlers.
        """
        if self.started:
            self.queue_listener.stop()
            self.started = False

        # QueueListener.stop() does not necessarily close handlers.
        for handler in self.queue_listener.handlers:
            try:
                handler.flush()
            finally:
                handler.close()

    def restore_root_logger(self) -> None:
        """
        Restore the root logger to its previous handlers and level.

        This is useful mainly for tests or interactive sessions.
        Most normal applications do not need to call this.
        """
        root = logging.getLogger()

        for handler in list(root.handlers):
            root.removeHandler(handler)

        if self.previous_root_handlers is not None:
            for handler in self.previous_root_handlers:
                root.addHandler(handler)

        if self.previous_root_level is not None:
            root.setLevel(self.previous_root_level)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_logging(
    *,
    log_dir: str | Path = "logs",
    app_name: str = "app",
    level: int = logging.INFO,
    console: bool = True,
    clear_existing_root_handlers: bool = True,
    capture_warnings: bool = True,
) -> LoggingQueueManager:
    """
    Configure queue-based logging.

    Parameters
    ----------
    log_dir:
        Directory where log files will be created.

    app_name:
        Prefix used in generated log filenames.

    level:
        Logging level for the root logger and handlers.

    console:
        If True, echo log records to the terminal.

    clear_existing_root_handlers:
        If True, replace existing root handlers with a QueueHandler.
        This is usually what you want in an application.

    capture_warnings:
        If True, route warnings.warn(...) messages into logging.

    Returns
    -------
    LoggingQueueManager
        Manager object. You may call manager.shutdown() explicitly.

    Generated files
    ---------------
    Example, with app_name="survey":

        survey 2026-05-03_18-42-11 ALL.log
        survey 2026-05-03_18-42-11 MAIN.log
        survey 2026-05-03_18-42-11 thread Worker-1.log
    """
    global _ACTIVE_MANAGER

    if _ACTIVE_MANAGER is not None:
        # Avoid accidentally stacking multiple QueueHandlers on root.
        shutdown_logging(restore_root=True)

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    safe_app_name = _safe_filename_part(app_name)
    run_timestamp = make_run_timestamp()
    main_thread_id = threading.main_thread().ident

    if main_thread_id is None:
        raise RuntimeError("Could not determine main thread id.")

    all_log_path = log_dir / f"{safe_app_name} {run_timestamp} ALL.log"
    main_log_path = log_dir / f"{safe_app_name} {run_timestamp} MAIN.log"

    log_format = (
        "%(asctime)s.%(msecs)03d "
        "[%(levelname)-8s] "
        "[%(threadName)s] "
        "%(name)s: "
        "%(message)s"
    )

    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(
        fmt=log_format,
        datefmt=date_format,
    )

    # Listener-side handlers.
    all_file_handler = logging.FileHandler(
        all_log_path,
        mode="a",
        encoding="utf-8",
    )
    all_file_handler.setLevel(level)
    all_file_handler.setFormatter(formatter)

    main_file_handler = logging.FileHandler(
        main_log_path,
        mode="a",
        encoding="utf-8",
    )
    main_file_handler.setLevel(level)
    main_file_handler.setFormatter(formatter)
    main_file_handler.addFilter(MainThreadOnlyFilter(main_thread_id))

    per_thread_handler = PerThreadFileHandler(
        log_dir=log_dir,
        app_name=safe_app_name,
        run_timestamp=run_timestamp,
        main_thread_id=main_thread_id,
        encoding="utf-8",
    )
    per_thread_handler.setLevel(level)
    per_thread_handler.setFormatter(formatter)
    per_thread_handler.addFilter(NonMainThreadOnlyFilter(main_thread_id))

    listener_handlers: list[logging.Handler] = [
        all_file_handler,
        main_file_handler,
        per_thread_handler,
    ]

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        listener_handlers.append(console_handler)

    log_queue: queue.Queue = queue.Queue(-1)

    queue_listener = logging.handlers.QueueListener(
        log_queue,
        *listener_handlers,
        respect_handler_level=True,
    )

    manager = LoggingQueueManager(
        log_dir=log_dir,
        app_name=safe_app_name,
        run_timestamp=run_timestamp,
        main_thread_id=main_thread_id,
        log_queue=log_queue,
        queue_listener=queue_listener,
        all_log_path=all_log_path,
        main_log_path=main_log_path,
    )

    root = logging.getLogger()

    manager.previous_root_handlers = list(root.handlers)
    manager.previous_root_level = root.level

    if clear_existing_root_handlers:
        for handler in list(root.handlers):
            root.removeHandler(handler)

    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(level)

    root.addHandler(queue_handler)
    root.setLevel(level)

    if capture_warnings:
        logging.captureWarnings(True)

    manager.start()
    _ACTIVE_MANAGER = manager

    atexit.register(shutdown_logging)

    startup_logger = logging.getLogger(__name__)
    startup_logger.info("Logging initialized")
    startup_logger.info("ALL log file: %s", all_log_path)
    startup_logger.info("MAIN log file: %s", main_log_path)

    return manager


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger.

    Examples
    --------
        logger = get_logger(__name__)
        logger.info("Hello")

    If name is None, returns the root logger.
    """
    return logging.getLogger(name)


def shutdown_logging(*, restore_root: bool = False) -> None:
    """
    Shutdown the active queue-based logging setup.

    Parameters
    ----------
    restore_root:
        If True, restore the root logger handlers and level that existed before
        setup_logging() was called.
    """
    global _ACTIVE_MANAGER

    if _ACTIVE_MANAGER is None:
        return

    manager = _ACTIVE_MANAGER
    _ACTIVE_MANAGER = None

    logging.getLogger(__name__).info("Logging shutting down")

    manager.shutdown()

    if restore_root:
        manager.restore_root_logger()


@contextmanager
def logging_context(
    *,
    log_dir: str | Path = "logs",
    app_name: str = "app",
    level: int = logging.INFO,
    console: bool = True,
    clear_existing_root_handlers: bool = True,
    capture_warnings: bool = True,
):
    """
    Context manager wrapper around setup_logging() / shutdown_logging().

    Example
    -------
        with logging_context(log_dir="logs", app_name="survey"):
            logger = get_logger(__name__)
            logger.info("Hello")
    """
    manager = setup_logging(
        log_dir=log_dir,
        app_name=app_name,
        level=level,
        console=console,
        clear_existing_root_handlers=clear_existing_root_handlers,
        capture_warnings=capture_warnings,
    )

    try:
        yield manager
    finally:
        shutdown_logging()


# ---------------------------------------------------------------------------
# Optional demo
# ---------------------------------------------------------------------------

def _demo_worker(worker_number: int) -> None:
    logger = get_logger(f"demo.worker.{worker_number}")

    logger.info("Worker %s started", worker_number)

    for i in range(3):
        logger.info("Worker %s message %s", worker_number, i)

    logger.info("Worker %s finished", worker_number)


def demo() -> None:
    """
    Run a small demonstration.

    This creates:
        logs/demo <timestamp> ALL.log
        logs/demo <timestamp> MAIN.log
        logs/demo <timestamp> thread Worker-A.log
        logs/demo <timestamp> thread Worker-B.log
    """
    with logging_context(log_dir="logs", app_name="demo", level=logging.DEBUG):
        logger = get_logger(__name__)

        logger.info("Main thread started")

        threads = [
            threading.Thread(
                target=_demo_worker,
                args=(1,),
                name="Worker-A",
            ),
            threading.Thread(
                target=_demo_worker,
                args=(2,),
                name="Worker-B",
            ),
        ]

        for thread in threads:
            thread.start()

        logger.info("Main thread is waiting for workers")

        for thread in threads:
            thread.join()

        logger.info("Main thread finished")


if __name__ == "__main__":
    demo()
    