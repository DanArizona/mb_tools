from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

import mb_tools.schwab_secure.cli as cli


def test_status_mode_does_not_construct_a_schwab_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ecfg_path = tmp_path / "secure_schwabdev.ecfg"
    ecfg_path.touch()
    print_status = Mock(return_value=0)
    make_client = Mock()
    monkeypatch.setattr(cli, "_print_status", print_status)
    monkeypatch.setattr(cli, "make_secure_schwab_client", make_client)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: "password")

    result = cli.main(["--ecfg", str(ecfg_path), "--status"])

    assert result == 0
    print_status.assert_called_once_with(ecfg_path, "password")
    make_client.assert_not_called()


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
