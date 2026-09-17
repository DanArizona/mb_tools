from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mb_tools.schwab_secure import (
    SecureSchwabConfig,
    SchwabCredentialPreflightError,
    SchwabTokenStatusError,
    read_schwab_token_status,
)


UTC = timezone.utc


def make_config(database: Path) -> SecureSchwabConfig:
    return SecureSchwabConfig(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=database,
        token_db_fernet_key="test-key",
    )


def write_tokens(
    database: Path,
    *,
    access_issued: str,
    refresh_issued: str,
    expires_in: int = 1_800,
) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE schwabdev (
                access_token_issued TEXT,
                refresh_token_issued TEXT,
                access_token TEXT,
                refresh_token TEXT,
                id_token TEXT,
                expires_in INTEGER,
                token_type TEXT,
                scope TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO schwabdev (
                access_token_issued,
                refresh_token_issued,
                expires_in
            ) VALUES (?, ?, ?)
            """,
            (access_issued, refresh_issued, expires_in),
        )


def test_reads_lifetime_metadata_without_token_values(tmp_path: Path) -> None:
    database = tmp_path / "tokens.db"
    observed = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    write_tokens(
        database,
        access_issued="2026-09-16T11:50:00+00:00",
        refresh_issued="2026-09-12T08:00:00+00:00",
        expires_in=1_800,
    )

    status = read_schwab_token_status(
        make_config(database),
        observed_at=observed,
    )

    assert status.tokens_db == database.resolve()
    assert status.access_remaining == timedelta(minutes=20)
    assert status.refresh_remaining == timedelta(days=2, hours=20)


def test_legacy_naive_timestamps_are_interpreted_as_utc(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tokens.db"
    observed = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    write_tokens(
        database,
        access_issued="2026-09-16T11:45:00",
        refresh_issued="2026-09-10T12:00:00",
    )

    status = read_schwab_token_status(
        make_config(database),
        observed_at=observed,
    )

    assert status.access_remaining == timedelta(minutes=15)
    assert status.refresh_remaining == timedelta(days=1)


def test_missing_database_is_reported(tmp_path: Path) -> None:
    database = tmp_path / "missing.db"

    with pytest.raises(SchwabTokenStatusError, match="does not exist"):
        read_schwab_token_status(make_config(database))


def test_empty_database_is_reported(tmp_path: Path) -> None:
    database = tmp_path / "tokens.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE schwabdev (
                access_token_issued TEXT,
                refresh_token_issued TEXT,
                expires_in INTEGER
            )
            """
        )

    with pytest.raises(SchwabTokenStatusError, match="no token record"):
        read_schwab_token_status(make_config(database))


def test_refresh_horizon_accepts_exact_expiration(tmp_path: Path) -> None:
    database = tmp_path / "tokens.db"
    observed = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    write_tokens(
        database,
        access_issued="2026-09-16T11:45:00+00:00",
        refresh_issued="2026-09-10T12:00:00+00:00",
    )
    status = read_schwab_token_status(
        make_config(database),
        observed_at=observed,
    )

    status.require_refresh_valid_through(status.refresh_token_expires_at)


def test_refresh_horizon_fails_closed_past_expiration(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tokens.db"
    observed = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    write_tokens(
        database,
        access_issued="2026-09-16T11:45:00+00:00",
        refresh_issued="2026-09-10T12:00:00+00:00",
    )
    status = read_schwab_token_status(
        make_config(database),
        observed_at=observed,
    )

    with pytest.raises(
        SchwabCredentialPreflightError,
        match="Run mb-schwab-auth",
    ):
        status.require_refresh_valid_through(
            status.refresh_token_expires_at + timedelta(microseconds=1)
        )
