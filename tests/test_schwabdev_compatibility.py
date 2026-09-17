from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

import schwabdev.tokens

from mb_tools.schwab_secure import SecureSchwabConfig, make_client_from_config


UTC = timezone.utc


def write_token_database(
    database: Path,
    *,
    access_issued: datetime,
    refresh_issued: datetime,
) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE schwabdev (
                access_token_issued TEXT NOT NULL,
                refresh_token_issued TEXT NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                id_token TEXT NOT NULL,
                expires_in INTEGER,
                token_type TEXT,
                scope TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO schwabdev VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                access_issued.isoformat(),
                refresh_issued.isoformat(),
                "access",
                "refresh",
                "id",
                1_800,
                "Bearer",
                "api",
            ),
        )


def test_client_factory_is_compatible_with_schwabdev_four(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tokens.db"
    now = datetime.now(UTC)
    write_token_database(
        database,
        access_issued=now,
        refresh_issued=now,
    )
    config = SecureSchwabConfig(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=database,
        # Schwabdev treats a short value as encryption disabled. The values
        # in this synthetic database are intentionally non-secret plaintext.
        token_db_fernet_key="test",
    )

    client = make_client_from_config(
        config,
        call_on_auth=lambda _auth_url: "",
    )

    assert client.tokens.access_token == "access"
    client.close()


def test_failed_interactive_auth_releases_exclusive_database_lock(
    tmp_path: Path,
) -> None:
    """Protect the exact Schwabdev 3.0.5 lock-leak failure mode."""

    assert tuple(int(part) for part in version("schwabdev").split(".")) >= (
        4,
        0,
        0,
    )
    database = tmp_path / "tokens.db"
    now = datetime.now(UTC)
    write_token_database(
        database,
        access_issued=now,
        refresh_issued=now - timedelta(days=6, hours=23, minutes=30),
    )

    tokens = schwabdev.tokens.Tokens(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        logger=logging.getLogger("test_schwabdev_compatibility"),
        tokens_db=str(database),
        call_for_auth=lambda _auth_url: "",
        open_browser_for_auth=False,
    )

    assert not tokens._conn.in_transaction
    with sqlite3.connect(database, timeout=0.1) as second_connection:
        second_connection.execute("BEGIN EXCLUSIVE")
        second_connection.rollback()
    tokens._conn.close()
