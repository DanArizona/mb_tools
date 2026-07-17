from __future__ import annotations

import os
from pathlib import Path

from mb_tools.config import load_mb_config


def _remove_mb_environment(monkeypatch) -> None:
    """
    Remove all effective MB_* environment variables for the duration
    of the current test.

    pytest's monkeypatch fixture restores them after the test finishes.
    """
    for name in list(os.environ):
        if name.startswith("MB_"):
            monkeypatch.delenv(name, raising=False)


def test_packaged_defaults_are_loaded(monkeypatch) -> None:
    _remove_mb_environment(monkeypatch)

    config = load_mb_config(
        dotenv_path=None,
        use_packaged_defaults=True,
        verbose=False,
    )

    assert config.values["MB_ENV_VERSION"] == "1"
    assert config.values["MB_SCANS"] == r"C:\MB\scans"
    assert config.values["MB_VAULT"] == r"C:\MB\vault"
    assert config.values["MB_TOOLS"] == r"C:\MB\tools"
    assert config.values["MB_CONFIG"] == r"C:\MB\config"

    assert config.sources["MB_ENV_VERSION"] == "defaults"
    assert config.sources["MB_SCANS"] == "defaults"
    assert config.sources["MB_VAULT"] == "defaults"

    assert config.errors == []


def test_windows_environment_overrides_packaged_default(monkeypatch) -> None:
    _remove_mb_environment(monkeypatch)
    monkeypatch.setenv("MB_SCANS", r"C:\test\windows-scans")

    config = load_mb_config(
        dotenv_path=None,
        use_packaged_defaults=True,
        verbose=False,
    )

    assert config.values["MB_SCANS"] == r"C:\test\windows-scans"
    assert config.sources["MB_SCANS"] == "env"


def test_project_dotenv_overrides_windows_environment(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _remove_mb_environment(monkeypatch)
    monkeypatch.setenv("MB_SCANS", r"C:\test\windows-scans")

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "MB_SCANS=C:\\test\\dotenv-scans\n",
        encoding="utf-8",
    )

    config = load_mb_config(
        dotenv_path=dotenv_path,
        use_packaged_defaults=True,
        verbose=False,
    )

    assert config.values["MB_SCANS"] == r"C:\test\dotenv-scans"
    assert config.sources["MB_SCANS"] == "dotenv"


def test_dotenv_only_mb_variable_is_accepted(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _remove_mb_environment(monkeypatch)

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "MB_TEST_DOTENV=dotenv-only\n",
        encoding="utf-8",
    )

    config = load_mb_config(
        dotenv_path=dotenv_path,
        use_packaged_defaults=False,
        verbose=False,
    )

    assert config.values["MB_TEST_DOTENV"] == "dotenv-only"
    assert config.sources["MB_TEST_DOTENV"] == "dotenv"
    assert config.errors == []


def test_non_mb_dotenv_key_is_reported_but_loading_continues(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _remove_mb_environment(monkeypatch)

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "MB_VALID=value-is-kept",
                "NOT_AN_MB_VARIABLE=value-is-rejected",
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = load_mb_config(
        dotenv_path=dotenv_path,
        use_packaged_defaults=False,
        verbose=False,
    )

    assert config.values["MB_VALID"] == "value-is-kept"
    assert config.sources["MB_VALID"] == "dotenv"

    assert "NOT_AN_MB_VARIABLE" not in config.values
    assert config.errors == [
        ".env contains non-MB_ key: NOT_AN_MB_VARIABLE"
    ]


def test_load_mb_config_does_not_modify_os_environ(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _remove_mb_environment(monkeypatch)
    monkeypatch.setenv("MB_EXISTING", "windows-value")

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "MB_EXISTING=dotenv-value",
                "MB_DOTENV_ONLY=another-value",
                "",
            ]
        ),
        encoding="utf-8",
    )

    environment_before = dict(os.environ)

    config = load_mb_config(
        dotenv_path=dotenv_path,
        use_packaged_defaults=True,
        verbose=False,
    )

    environment_after = dict(os.environ)

    assert config.values["MB_EXISTING"] == "dotenv-value"
    assert config.values["MB_DOTENV_ONLY"] == "another-value"
    assert environment_after == environment_before
