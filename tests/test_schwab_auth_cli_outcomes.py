"""Offline regression tests for CLI authorization outcomes."""
from __future__ import annotations

import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mb_tools.schwab_secure import cli

UTC = timezone.utc


def status(refresh_seconds: int, access_seconds: int = 120):
    now = datetime.now(UTC)
    return SimpleNamespace(
        tokens_db=Path("tokens.db"),
        observed_at=now,
        access_token_expires_at=now + timedelta(seconds=access_seconds),
        refresh_token_expires_at=now + timedelta(seconds=refresh_seconds),
        access_remaining=timedelta(seconds=access_seconds),
        refresh_remaining=timedelta(seconds=refresh_seconds),
    )


class AuthorizationCliTests(unittest.TestCase):
    def run_cli(self, *, refresh_seconds: int | None, client_failure=False):
        with tempfile.TemporaryDirectory() as temp:
            ecfg = Path(temp) / "secure.ecfg"
            ecfg.write_text("placeholder", encoding="utf-8")
            config = SimpleNamespace(tokens_db=Path(temp) / "tokens.db")
            stdout, stderr = io.StringIO(), io.StringIO()
            def factory(*args, **kwargs):
                if client_failure:
                    raise RuntimeError("authorization failed")
                return SimpleNamespace(close=lambda: None)
            reader = (lambda _config: status(refresh_seconds)) if refresh_seconds is not None else (lambda _config: (_ for _ in ()).throw(cli.SchwabTokenStatusError("unreadable")))
            with patch.object(cli.getpass, "getpass", return_value="dummy"), \
                 patch.object(cli, "load_secure_schwab_config", return_value=config), \
                 patch.object(cli, "make_client_from_config", side_effect=factory), \
                 patch.object(cli, "read_schwab_token_status", side_effect=reader), \
                 patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                result = cli.main(["--ecfg", str(ecfg)])
            return result, stdout.getvalue() + stderr.getvalue()

    def test_new_refresh_token_is_verified(self):
        code, output = self.run_cli(refresh_seconds=86400)
        self.assertEqual(code, 0)
        self.assertIn("AUTHORIZATION: VERIFIED", output)
        self.assertNotIn("should now be updated", output)

    def test_expired_refresh_after_client_creation_is_failure(self):
        code, output = self.run_cli(refresh_seconds=-1)
        self.assertNotEqual(code, 0)
        self.assertIn("AUTHORIZATION: FAILED", output)

    def test_unreadable_persisted_token_is_not_success(self):
        code, output = self.run_cli(refresh_seconds=None)
        self.assertNotEqual(code, 0)
        self.assertIn("AUTHORIZATION: UNVERIFIED", output)

    def test_client_failure_does_not_claim_verified(self):
        code, output = self.run_cli(refresh_seconds=86400, client_failure=True)
        self.assertNotEqual(code, 0)
        self.assertNotIn("AUTHORIZATION: VERIFIED", output)

    def test_status_expired_is_nonzero(self):
        output = io.StringIO()
        with patch.object(cli, "read_schwab_token_status", return_value=status(-5)), patch("sys.stdout", output):
            code = cli._print_status(SimpleNamespace())
        self.assertNotEqual(code, 0)
        self.assertIn("AUTHORIZATION: EXPIRED", output.getvalue())

    def test_status_valid_is_zero(self):
        output = io.StringIO()
        with patch.object(cli, "read_schwab_token_status", return_value=status(86400, -1)), patch("sys.stdout", output):
            code = cli._print_status(SimpleNamespace())
        self.assertEqual(code, 0)
        self.assertIn("AUTHORIZATION: VALID", output.getvalue())


if __name__ == "__main__":
    unittest.main()
