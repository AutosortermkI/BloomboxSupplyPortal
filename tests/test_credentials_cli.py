import io
import unittest
from unittest import mock

from scrape import credentials
from scrape import manual_login
from scrape.core.vault import Credential


class CredentialsCliTests(unittest.TestCase):
    @mock.patch("scrape.credentials.vault.store_keychain_password")
    @mock.patch("scrape.credentials.vault.save_metadata_entry")
    def test_set_reads_password_from_stdin_and_writes_metadata_and_keychain(
        self,
        mock_save_metadata,
        mock_store_password,
    ):
        stdin = io.StringIO("real-secret\n")

        stdout = io.StringIO()
        with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
            rc = credentials.main(
                [
                    "set",
                    "--id",
                    "110",
                    "--url",
                    "https://www.waltersgardens.com/customer/account/login/",
                    "--user",
                    "buyer@example.com",
                    "--account",
                    "A-123",
                    "--password-stdin",
                ]
            )

        self.assertEqual(rc, 0)
        mock_save_metadata.assert_called_once()
        self.assertEqual(mock_save_metadata.call_args.args[0], 110)
        self.assertEqual(
            mock_save_metadata.call_args.kwargs["url"],
            "https://www.waltersgardens.com/customer/account/login/",
        )
        self.assertEqual(mock_save_metadata.call_args.kwargs["user"], "buyer@example.com")
        self.assertEqual(mock_save_metadata.call_args.kwargs["account"], "A-123")
        mock_store_password.assert_called_once_with(
            110,
            "buyer@example.com",
            "real-secret",
        )

    @mock.patch("scrape.credentials.manual_login.capture_manual_login_session")
    @mock.patch("scrape.credentials.vault.load_vault")
    @mock.patch("scrape.credentials.vault.load_metadata")
    def test_login_session_uses_saved_credential_without_printing_secret(
        self,
        mock_load_metadata,
        mock_load_vault,
        mock_capture,
    ):
        mock_load_metadata.return_value = {
            43: {
                "url": "https://www.americannativeplants.com/my-account/",
                "user": "buyer@example.com",
            }
        }
        mock_load_vault.return_value = {
            43: Credential(
                supplier_id=43,
                url="https://www.americannativeplants.com/my-account/",
                user="buyer@example.com",
                password="real-secret",
            )
        }
        mock_capture.return_value = manual_login.ManualLoginResult(
            supplier_id=43,
            login_url="https://www.americannativeplants.com/my-account/",
            current_url="https://www.americannativeplants.com/my-account/",
            storage_state_path="/tmp/supplier_43.storage_state.json",
            success=True,
            reasons=["text:logout"],
        )

        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            rc = credentials.main(["login-session", "--id", "43"])

        self.assertEqual(rc, 0)
        mock_capture.assert_called_once()
        self.assertEqual(mock_capture.call_args.kwargs["supplier_id"], 43)
        self.assertEqual(
            mock_capture.call_args.kwargs["login_url"],
            "https://www.americannativeplants.com/my-account/",
        )
        self.assertNotIn("real-secret", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
