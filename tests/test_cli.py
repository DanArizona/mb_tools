from __future__ import annotations

import shutil
import subprocess
from importlib.metadata import distribution

import pytest


EXPECTED_ENTRY_POINTS = {
    "mb-env-report": "mb_tools.env_report:main",
    "mb-pwidget-tree": "mb_tools.pwidget_tree:main",
    "mb-window-survey": "mb_tools.window_survey:main",
    "mb-schwab-auth": "mb_tools.schwab_secure.cli:main",
    "mb-scan-command": "mb_tools.scan_command:main",
}


def test_expected_console_entry_points_are_installed() -> None:
    """
    Verify that the installed mb-tools distribution declares all
    expected command-line entry points.
    """
    dist = distribution("mb-tools")

    installed_entry_points = {
        entry_point.name: entry_point.value
        for entry_point in dist.entry_points
        if entry_point.group == "console_scripts"
    }

    for command_name, expected_target in EXPECTED_ENTRY_POINTS.items():
        assert installed_entry_points.get(command_name) == expected_target


@pytest.mark.parametrize("command_name", EXPECTED_ENTRY_POINTS)
def test_cli_help_starts_successfully(command_name: str) -> None:
    """
    Run each installed console command with --help.

    This verifies that:
      - the generated executable exists;
      - the entry-point module imports;
      - immediate dependencies import;
      - argparse starts successfully;
      - --help exits with status zero.
    """
    executable = shutil.which(command_name)

    assert executable is not None, (
        f"Console command {command_name!r} was not found on PATH"
    )

    result = subprocess.run(
        [executable, "--help"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, (
        f"{command_name} --help failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    assert "usage:" in result.stdout.lower()
    assert command_name in result.stdout
