import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scrape.core import vault


class CredentialVaultTests(unittest.TestCase):
    def test_load_vault_does_not_auto_discover_plaintext_exports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "bloombox_vault_2026-04-27.json"
            export_path.write_text(
                json.dumps(
                    {
                        "110": {
                            "url": "https://example.com/login",
                            "user": "buyer@example.com",
                            "pass": "secret",
                        }
                    }
                )
            )

            env = {vault.METADATA_PATH_ENV: str(Path(tmpdir) / "credentials.json")}
            with mock.patch.dict(os.environ, env, clear=True), mock.patch(
                "scrape.core.vault.DEFAULT_SEARCH_PATHS", [Path(tmpdir)]
            ):
                self.assertEqual(vault.load_vault(), {})

    def test_load_vault_reads_explicit_legacy_json_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "legacy-vault.json"
            export_path.write_text(
                json.dumps(
                    {
                        "110": {
                            "url": "https://example.com/login",
                            "user": "buyer@example.com",
                            "pass": "secret",
                            "acct": "A-123",
                            "savedAt": "2026-04-27T12:00:00Z",
                        }
                    }
                )
            )

            with self.assertLogs("bloombox.vault", level="WARNING"):
                creds = vault.load_vault(path=export_path)

            self.assertEqual(creds[110].url, "https://example.com/login")
            self.assertEqual(creds[110].user, "buyer@example.com")
            self.assertEqual(creds[110].password, "secret")
            self.assertEqual(creds[110].account, "A-123")

    def test_load_vault_reads_keychain_passwords_from_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "credentials.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "110": {
                            "url": "https://example.com/login",
                            "user": "buyer@example.com",
                            "acct": "A-123",
                            "savedAt": "2026-04-27T12:00:00Z",
                        }
                    }
                )
            )

            def fake_keychain_reader(supplier_id, username):
                self.assertEqual(supplier_id, 110)
                self.assertEqual(username, "buyer@example.com")
                return "secret-from-keychain"

            creds = vault.load_vault(
                supplier_ids=[110],
                metadata_path=metadata_path,
                keychain_reader=fake_keychain_reader,
            )

            self.assertEqual(creds[110].url, "https://example.com/login")
            self.assertEqual(creds[110].user, "buyer@example.com")
            self.assertEqual(creds[110].password, "secret-from-keychain")
            self.assertEqual(creds[110].account, "A-123")

    def test_save_metadata_entry_writes_no_password_file_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "credentials.json"

            vault.save_metadata_entry(
                110,
                url="https://example.com/login",
                user="buyer@example.com",
                account="A-123",
                metadata_path=metadata_path,
                saved_at="2026-04-27T12:00:00Z",
            )

            raw = metadata_path.read_text()
            self.assertNotIn("password", raw.lower())
            self.assertNotIn("secret", raw.lower())
            self.assertEqual(stat.S_IMODE(metadata_path.stat().st_mode), 0o600)

            saved = json.loads(raw)
            self.assertEqual(saved["110"]["url"], "https://example.com/login")
            self.assertEqual(saved["110"]["user"], "buyer@example.com")
            self.assertEqual(saved["110"]["acct"], "A-123")

    def test_store_keychain_password_uses_supplier_service_and_updates_existing_item(self):
        calls = []

        class Completed:
            returncode = 0
            stderr = ""

        def fake_runner(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return Completed()

        vault.store_keychain_password(
            110,
            "buyer@example.com",
            "secret",
            runner=fake_runner,
        )

        cmd, kwargs = calls[0]
        self.assertEqual(cmd[0], "security")
        self.assertIn("add-generic-password", cmd)
        self.assertIn("-U", cmd)
        self.assertIn("com.bloombox.supply-portal.supplier.110", cmd)
        self.assertIn("buyer@example.com", cmd)
        self.assertIn("secret", cmd)
        self.assertTrue(kwargs["capture_output"])


if __name__ == "__main__":
    unittest.main()
