from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest

import mb_tools.schwab_secure.client as client_module
import mb_tools.schwab_secure.config as config_module
from mb_tools.schwab_secure import (
    REQUIRED_ECFG_KEYS,
    SecureSchwabConfig,
    SecureSchwabConfigError,
    config_from_dict,
    load_secure_schwab_config,
    make_client_from_config,
    make_secure_schwab_client,
    validate_schwabdev_key_shape,
    validate_secure_schwab_dict,
)


def make_valid_config_dict(tokens_db: Path) -> dict[str, str]:
    """
    Return a synthetic but structurally valid Schwab configuration.

    These are test-only values and are not real credentials.
    """
    return {
        "SCHWAB_APP_KEY": "A" * 16,
        "SCHWAB_APP_SECRET": "B" * 16,
        "SCHWAB_CALLBACK_URL": "https://127.0.0.1",
        "SCHWAB_TOKENS_DB": str(tokens_db),
        "SCHWAB_TOKEN_DB_FERNET_KEY": "fake-fernet-key",
    }


def test_required_key_list_is_complete() -> None:
    assert REQUIRED_ECFG_KEYS == (
        "SCHWAB_APP_KEY",
        "SCHWAB_APP_SECRET",
        "SCHWAB_CALLBACK_URL",
        "SCHWAB_TOKENS_DB",
        "SCHWAB_TOKEN_DB_FERNET_KEY",
    )


def test_valid_config_is_accepted_and_converted(
    tmp_path: Path,
) -> None:
    tokens_db = tmp_path / "tokens" / "schwab_tokens.db"
    data = make_valid_config_dict(tokens_db)

    validate_secure_schwab_dict(data)
    config = config_from_dict(data)

    assert isinstance(config, SecureSchwabConfig)
    assert config.app_key == "A" * 16
    assert config.app_secret == "B" * 16
    assert config.callback_url == "https://127.0.0.1"
    assert config.tokens_db == tokens_db
    assert config.token_db_fernet_key == "fake-fernet-key"


def test_missing_required_key_is_rejected(
    tmp_path: Path,
) -> None:
    data = make_valid_config_dict(tmp_path / "tokens.db")
    del data["SCHWAB_APP_SECRET"]

    with pytest.raises(
        SecureSchwabConfigError,
        match="SCHWAB_APP_SECRET",
    ):
        validate_secure_schwab_dict(data)


@pytest.mark.parametrize(
    "invalid_value",
    [
        "   ",
        123,
    ],
)
def test_blank_or_nonstring_required_value_is_rejected(
    tmp_path: Path,
    invalid_value: object,
) -> None:
    data: dict[str, object] = {}
    data.update(
        make_valid_config_dict(tmp_path / "tokens.db")
    )
    data["SCHWAB_CALLBACK_URL"] = invalid_value

    with pytest.raises(
        SecureSchwabConfigError,
        match="SCHWAB_CALLBACK_URL",
    ):
        validate_secure_schwab_dict(data)


def test_odd_length_app_key_is_rejected() -> None:
    with pytest.raises(
        SecureSchwabConfigError,
        match="SCHWAB_APP_KEY has odd length",
    ):
        validate_schwabdev_key_shape(
            app_key="A" * 15,
            app_secret="B" * 18,
        )


def test_odd_length_app_secret_is_rejected() -> None:
    with pytest.raises(
        SecureSchwabConfigError,
        match="SCHWAB_APP_SECRET has odd length",
    ):
        validate_schwabdev_key_shape(
            app_key="A" * 18,
            app_secret="B" * 15,
        )


def test_combined_key_length_is_validated() -> None:
    with pytest.raises(
        SecureSchwabConfigError,
        match="combined length less than 32",
    ):
        validate_schwabdev_key_shape(
            app_key="A" * 8,
            app_secret="B" * 8,
        )


def test_load_secure_schwab_config_uses_decrypted_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ecfg_path = tmp_path / "secure_schwabdev.ecfg"
    tokens_db = tmp_path / "tokens.db"
    decrypted_data = make_valid_config_dict(tokens_db)

    load_ecfg_mock = Mock(return_value=decrypted_data)
    monkeypatch.setattr(
        config_module,
        "load_ecfg",
        load_ecfg_mock,
    )

    config = load_secure_schwab_config(
        ecfg_path,
        password="test-password",
    )

    load_ecfg_mock.assert_called_once_with(
        ecfg_path,
        "test-password",
    )

    assert config.app_key == "A" * 16
    assert config.app_secret == "B" * 16
    assert config.tokens_db == tokens_db


def test_nonmapping_decrypted_value_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        config_module,
        "load_ecfg",
        lambda path, password: ["not", "a", "mapping"],
    )

    with pytest.raises(
        SecureSchwabConfigError,
        match="dictionary-like object",
    ):
        load_secure_schwab_config(
            tmp_path / "invalid.ecfg",
            password="test-password",
        )


def test_make_client_from_config_uses_schwabdev_without_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tokens_db = tmp_path / "nested" / "schwab_tokens.db"

    config = SecureSchwabConfig(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=tokens_db,
        token_db_fernet_key="fake-fernet-key",
    )

    fake_client = object()
    client_constructor = Mock(return_value=fake_client)

    fake_schwabdev = ModuleType("schwabdev")
    fake_schwabdev.Client = client_constructor  # type: ignore[attr-defined]

    monkeypatch.setitem(
        sys.modules,
        "schwabdev",
        fake_schwabdev,
    )

    def fake_auth_callback(auth_url: str) -> str:
        return "https://127.0.0.1/?code=fake-code"

    result = make_client_from_config(
        config,
        timeout=25,
        call_on_auth=fake_auth_callback,
    )

    assert result is fake_client
    assert tokens_db.parent.exists()

    client_constructor.assert_called_once_with(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=str(tokens_db),
        encryption="fake-fernet-key",
        timeout=25,
        call_on_auth=fake_auth_callback,
        open_browser_for_auth=False,
    )


def test_make_secure_client_delegates_loading_and_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ecfg_path = tmp_path / "secure_schwabdev.ecfg"

    config = SecureSchwabConfig(
        app_key="A" * 16,
        app_secret="B" * 16,
        callback_url="https://127.0.0.1",
        tokens_db=tmp_path / "tokens.db",
        token_db_fernet_key="fake-fernet-key",
    )

    fake_client = object()

    load_mock = Mock(return_value=config)
    create_mock = Mock(return_value=fake_client)

    monkeypatch.setattr(
        client_module,
        "load_secure_schwab_config",
        load_mock,
    )
    monkeypatch.setattr(
        client_module,
        "make_client_from_config",
        create_mock,
    )

    def fake_auth_callback(auth_url: str) -> str:
        return "https://127.0.0.1/?code=fake-code"

    result = make_secure_schwab_client(
        ecfg_path,
        password="test-password",
        timeout=30,
        call_on_auth=fake_auth_callback,
    )

    assert result is fake_client

    load_mock.assert_called_once_with(
        ecfg_path,
        "test-password",
    )

    create_mock.assert_called_once_with(
        config,
        timeout=30,
        call_on_auth=fake_auth_callback,
    )
