import io
import unittest
from unittest import mock

from scrape import credentials


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


if __name__ == "__main__":
    unittest.main()
