from __future__ import annotations

from pathlib import Path

import pytest

from mb_tools.secure_config import (
    EcfgDecryptError,
    EcfgFormatError,
    load_ecfg,
    read_ecfg_value,
    save_ecfg,
)


def test_ecfg_round_trip_and_value_lookup(tmp_path: Path) -> None:
    """
    Saving and loading an encrypted configuration should reproduce
    the original dictionary exactly.
    """
    ecfg_path = tmp_path / "test_config.ecfg"

    original = {
        "client_id": "fake-client-id",
        "client_secret": "fake-client-secret",
        "callback_url": "https://127.0.0.1",
        "settings": {
            "timeout": 10,
            "enabled": True,
        },
        "symbols": ["AAPL", "MSFT", "NVDA"],
    }

    save_ecfg(
        ecfg_path,
        original,
        password="correct-test-password",
    )

    restored = load_ecfg(
        ecfg_path,
        password="correct-test-password",
    )

    assert ecfg_path.exists()
    assert restored == original

    assert (
        read_ecfg_value(
            ecfg_path,
            "client_id",
            password="correct-test-password",
        )
        == "fake-client-id"
    )

    assert (
        read_ecfg_value(
            ecfg_path,
            "missing_key",
            password="correct-test-password",
            default="fallback",
        )
        == "fallback"
    )


def test_incorrect_password_raises_decrypt_error(
    tmp_path: Path,
) -> None:
    """
    Loading a valid file with the wrong password should raise
    EcfgDecryptError.
    """
    ecfg_path = tmp_path / "wrong_password.ecfg"

    save_ecfg(
        ecfg_path,
        {"secret": "not-a-real-secret"},
        password="correct-password",
    )

    with pytest.raises(EcfgDecryptError):
        load_ecfg(
            ecfg_path,
            password="incorrect-password",
        )


def test_invalid_file_header_raises_format_error(
    tmp_path: Path,
) -> None:
    """
    A file without the required MB_ECFG_V1 header should be rejected.
    """
    ecfg_path = tmp_path / "invalid_header.ecfg"
    ecfg_path.write_bytes(b"This is not an mb_tools ecfg file.")

    with pytest.raises(EcfgFormatError):
        load_ecfg(
            ecfg_path,
            password="test-password",
        )


def test_incomplete_ecfg_file_raises_format_error(
    tmp_path: Path,
) -> None:
    """
    A file with the correct header but insufficient encrypted data
    should be rejected.
    """
    ecfg_path = tmp_path / "incomplete.ecfg"

    # Correct magic header, but not enough data for a complete salt
    # and encrypted payload.
    ecfg_path.write_bytes(b"MB_ECFG_V1\nshort")

    with pytest.raises(EcfgFormatError):
        load_ecfg(
            ecfg_path,
            password="test-password",
        )


def test_save_ecfg_requires_dictionary(tmp_path: Path) -> None:
    """
    save_ecfg accepts dictionaries only.
    """
    ecfg_path = tmp_path / "not_a_dictionary.ecfg"

    with pytest.raises(TypeError, match="data must be a dictionary"):
        save_ecfg(
            ecfg_path,
            ["not", "a", "dictionary"],  # type: ignore[arg-type]
            password="test-password",
        )

    assert not ecfg_path.exists()
