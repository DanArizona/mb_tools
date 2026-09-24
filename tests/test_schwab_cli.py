from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import mb_tools.schwab_secure.cli as cli
from mb_tools.schwab_secure import SecureSchwabConfig


def test_status_mode_does_not_construct_a_schwab_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ecfg_path = tmp_path / "secure_schwabdev.ecfg"
    ecfg_path.touch()
    config = SecureSchwabConfig(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=tmp_path / "tokens.db",
        token_db_fernet_key="test-key",
    )
    print_status = Mock(return_value=0)
    make_client = Mock()
    load_config = Mock(return_value=config)
    monkeypatch.setattr(cli, "_print_status", print_status)
    monkeypatch.setattr(cli, "make_client_from_config", make_client)
    monkeypatch.setattr(cli, "load_secure_schwab_config", load_config)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: "password")

    result = cli.main(["--ecfg", str(ecfg_path), "--status"])

    assert result == 0
    load_config.assert_called_once_with(ecfg_path, "password")
    print_status.assert_called_once_with(config)
    make_client.assert_not_called()


def test_reports_config_acceptance_before_client_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ecfg_path = tmp_path / "secure_schwabdev.ecfg"
    ecfg_path.touch()
    config = SecureSchwabConfig(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=tmp_path / "tokens.db",
        token_db_fernet_key="test-key",
    )
    events: list[str] = []
    monkeypatch.setattr(
        cli,
        "load_secure_schwab_config",
        lambda _path, _password: events.append("loaded") or config,
    )
    monkeypatch.setattr(
        cli,
        "make_client_from_config",
        lambda _config, **_kwargs: events.append("client") or object(),
    )
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: "password")

    result = cli.main(["--ecfg", str(ecfg_path)])

    assert result == 0
    assert events == ["loaded", "client"]
    assert "Encrypted configuration accepted." in capsys.readouterr().out


def test_force_mode_uses_loaded_config_without_normal_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ecfg_path = tmp_path / "secure_schwabdev.ecfg"
    ecfg_path.touch()
    database = tmp_path / "tokens.db"
    backup = tmp_path / "tokens.before_forced_reauth.db"
    config = SecureSchwabConfig(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=database,
        token_db_fernet_key="test-key",
    )
    refresh_expires = datetime(2026, 9, 30, tzinfo=timezone.utc)
    force_result = SimpleNamespace(
        tokens_db=database,
        backup_path=backup,
        status=SimpleNamespace(refresh_token_expires_at=refresh_expires),
    )
    force = Mock(return_value=force_result)
    make_client = Mock()
    monkeypatch.setattr(
        cli,
        "load_secure_schwab_config",
        Mock(return_value=config),
    )
    monkeypatch.setattr(cli, "force_schwab_reauthorization", force)
    monkeypatch.setattr(cli, "make_client_from_config", make_client)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: "password")

    result = cli.main(
        [
            "--ecfg",
            str(ecfg_path),
            "--force-reauthorize",
            "--timeout",
            "17",
        ]
    )

    assert result == 0
    force.assert_called_once_with(
        config,
        timeout=17,
        call_on_auth=cli.console_auth_callback,
    )
    make_client.assert_not_called()
    output = capsys.readouterr().out
    assert "Encrypted configuration accepted." in output
    assert "Forced Schwab reauthorization: PASS" in output
    assert str(backup) in output


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (90, "1m 30s"),
        (-90, "EXPIRED by 1m 30s"),
        (90_061, "1d 1h 1m 1s"),
    ],
)
def test_remaining_text(seconds: float, expected: str) -> None:
    assert cli._remaining_text(seconds) == expected
