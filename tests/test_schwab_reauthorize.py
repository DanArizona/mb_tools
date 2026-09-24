from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mb_tools.schwab_secure import (
    SchwabForceReauthorizationError,
    SchwabTokenStatus,
    SchwabTokenStatusError,
    SecureSchwabConfig,
    force_schwab_reauthorization,
)


UTC = timezone.utc


class FakeClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def make_config(database: Path) -> SecureSchwabConfig:
    return SecureSchwabConfig(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=database,
        token_db_fernet_key="test-key",
    )


def make_status(
    database: Path,
    *,
    refresh_issued: datetime,
) -> SchwabTokenStatus:
    observed = datetime(2026, 9, 23, 12, tzinfo=UTC)
    return SchwabTokenStatus(
        tokens_db=database.resolve(),
        observed_at=observed,
        access_token_issued_at=observed,
        refresh_token_issued_at=refresh_issued,
        access_token_expires_at=observed + timedelta(minutes=30),
        refresh_token_expires_at=refresh_issued + timedelta(days=7),
    )


def test_forced_reauthorization_retains_backup_and_verifies_new_token(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tokens.db"
    database.write_bytes(b"old-token-database")
    config = make_config(database)
    old_status = make_status(
        database,
        refresh_issued=datetime(2026, 9, 20, tzinfo=UTC),
    )
    new_status = make_status(
        database,
        refresh_issued=datetime(2026, 9, 23, tzinfo=UTC),
    )
    statuses = iter((old_status, new_status))
    client = FakeClient()

    def client_factory(_config: SecureSchwabConfig, **_kwargs: object) -> object:
        assert not database.exists()
        database.write_bytes(b"new-token-database")
        return client

    result = force_schwab_reauthorization(
        config,
        observed_at=datetime(2026, 9, 23, 13, tzinfo=UTC),
        client_factory=client_factory,
        status_reader=lambda _config: next(statuses),
    )

    assert client.closed
    assert database.read_bytes() == b"new-token-database"
    assert result.backup_path is not None
    assert result.backup_path.read_bytes() == b"old-token-database"
    assert result.status is new_status


def test_failed_authorization_restores_original_database(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tokens.db"
    database.write_bytes(b"old-token-database")
    config = make_config(database)

    def client_factory(_config: SecureSchwabConfig, **_kwargs: object) -> object:
        database.write_bytes(b"partial-new-database")
        raise RuntimeError("simulated OAuth failure")

    with pytest.raises(
        SchwabForceReauthorizationError,
        match="original token database restored",
    ):
        force_schwab_reauthorization(
            config,
            observed_at=datetime(2026, 9, 23, 13, tzinfo=UTC),
            client_factory=client_factory,
            status_reader=lambda _config: make_status(
                database,
                refresh_issued=datetime(2026, 9, 20, tzinfo=UTC),
            ),
        )

    assert database.read_bytes() == b"old-token-database"
    assert not list(tmp_path.glob("*.before_forced_reauth_*.db"))


def test_verification_failure_restores_original_database(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tokens.db"
    database.write_bytes(b"old-token-database")
    config = make_config(database)
    calls = 0

    def status_reader(_config: SecureSchwabConfig) -> SchwabTokenStatus:
        nonlocal calls
        calls += 1
        if calls == 1:
            return make_status(
                database,
                refresh_issued=datetime(2026, 9, 20, tzinfo=UTC),
            )
        raise SchwabTokenStatusError("simulated unreadable replacement")

    def client_factory(_config: SecureSchwabConfig, **_kwargs: object) -> object:
        database.write_bytes(b"unreadable-new-database")
        return FakeClient()

    with pytest.raises(
        SchwabForceReauthorizationError,
        match="simulated unreadable replacement",
    ):
        force_schwab_reauthorization(
            config,
            observed_at=datetime(2026, 9, 23, 13, tzinfo=UTC),
            client_factory=client_factory,
            status_reader=status_reader,
        )

    assert database.read_bytes() == b"old-token-database"


def test_refuses_rotation_while_sqlite_sidecar_exists(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tokens.db"
    database.write_bytes(b"old-token-database")
    Path(f"{database}-wal").write_bytes(b"active")

    with pytest.raises(
        SchwabForceReauthorizationError,
        match="close every Schwab client",
    ):
        force_schwab_reauthorization(
            make_config(database),
            observed_at=datetime(2026, 9, 23, 13, tzinfo=UTC),
        )

    assert database.read_bytes() == b"old-token-database"


def test_keyboard_interrupt_restores_original_database(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tokens.db"
    database.write_bytes(b"old-token-database")
    config = make_config(database)

    def client_factory(_config: SecureSchwabConfig, **_kwargs: object) -> object:
        database.write_bytes(b"partial-new-database")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        force_schwab_reauthorization(
            config,
            observed_at=datetime(2026, 9, 23, 13, tzinfo=UTC),
            client_factory=client_factory,
            status_reader=lambda _config: make_status(
                database,
                refresh_issued=datetime(2026, 9, 20, tzinfo=UTC),
            ),
        )

    assert database.read_bytes() == b"old-token-database"
