"""
Credential loader for login-required supplier adapters.

The active model keeps passwords in the local OS credential store and keeps
non-secret supplier metadata in a small JSON file:

    ~/.config/bloombox/credentials.json

That metadata file contains supplier IDs, login URLs, usernames, account
numbers, and saved timestamps. Passwords are fetched from macOS Keychain using
the supplier ID and username. Legacy plaintext dashboard exports are still
readable only when explicitly passed via ``path`` or ``BLOOMBOX_VAULT_PATH``;
the runner no longer auto-discovers JSON files from Downloads or the repo.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

DEFAULT_SEARCH_PATHS = [
    Path.home() / "Downloads",
    Path.home() / "BloomboxSupplyPortal" / "scrape" / "vault",
    Path(__file__).resolve().parents[1] / "vault",
]
DEFAULT_METADATA_PATH = Path.home() / ".config" / "bloombox" / "credentials.json"
METADATA_PATH_ENV = "BLOOMBOX_CREDENTIALS_FILE"
LEGACY_VAULT_PATH_ENV = "BLOOMBOX_VAULT_PATH"
KEYCHAIN_SERVICE_PREFIX_ENV = "BLOOMBOX_KEYCHAIN_SERVICE_PREFIX"
DEFAULT_KEYCHAIN_SERVICE_PREFIX = "com.bloombox.supply-portal.supplier"

log = logging.getLogger("bloombox.vault")

KeychainReader = Callable[[int, str], Optional[str]]


@dataclass
class Credential:
    supplier_id: int
    url: str
    user: str
    password: str
    account: str = ""
    saved_at: str = ""
    source: str = ""

    @classmethod
    def from_dict(cls, sid: int, d: dict) -> "Credential":
        return cls(
            supplier_id=sid,
            url=d.get("url", ""),
            user=d.get("user", ""),
            password=d.get("pass", ""),
            account=d.get("acct", ""),
            saved_at=d.get("savedAt", ""),
            source=d.get("source", ""),
        )


def credential_metadata_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    override = os.environ.get(METADATA_PATH_ENV)
    if override:
        return Path(override).expanduser()
    return DEFAULT_METADATA_PATH


def keychain_service_name(supplier_id: int) -> str:
    prefix = os.environ.get(
        KEYCHAIN_SERVICE_PREFIX_ENV,
        DEFAULT_KEYCHAIN_SERVICE_PREFIX,
    )
    return f"{prefix}.{supplier_id}"


def find_latest_legacy_vault() -> Optional[Path]:
    """Find a legacy plaintext export for manual migration only."""
    candidates: list[Path] = []
    for base in DEFAULT_SEARCH_PATHS:
        if not base.exists():
            continue
        candidates.extend(base.glob("bloombox_vault_*.json"))
        candidates.extend(base.glob("vault.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _read_json_object(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text())
    except Exception as exc:
        log.warning("failed to read credential metadata %s: %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        log.warning("credential metadata %s is not a JSON object", path)
        return {}
    return raw


def load_metadata(path: Path | str | None = None) -> dict[int, dict]:
    path = credential_metadata_path(path)
    if not path.exists():
        return {}
    raw = _read_json_object(path)
    out: dict[int, dict] = {}
    for k, v in raw.items():
        try:
            sid = int(k)
        except Exception:
            continue
        if isinstance(v, dict):
            out[sid] = dict(v)
    return out


def write_metadata(metadata: dict[int, dict], path: Path | str | None = None) -> Path:
    path = credential_metadata_path(path)
    parent_existed = path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not parent_existed:
        os.chmod(path.parent, 0o700)

    normalized = {
        str(int(sid)): {
            "url": str(entry.get("url") or ""),
            "user": str(entry.get("user") or ""),
            "acct": str(entry.get("acct") or ""),
            "savedAt": str(entry.get("savedAt") or ""),
        }
        for sid, entry in sorted(metadata.items())
    }
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n")
    os.chmod(tmp_path, 0o600)
    tmp_path.replace(path)
    os.chmod(path, 0o600)
    return path


def save_metadata_entry(
    supplier_id: int,
    *,
    url: str,
    user: str,
    account: str = "",
    metadata_path: Path | str | None = None,
    saved_at: str | None = None,
) -> Path:
    metadata = load_metadata(metadata_path)
    metadata[int(supplier_id)] = {
        "url": url,
        "user": user,
        "acct": account,
        "savedAt": saved_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return write_metadata(metadata, metadata_path)


def delete_metadata_entry(
    supplier_id: int,
    *,
    metadata_path: Path | str | None = None,
) -> Path:
    metadata = load_metadata(metadata_path)
    metadata.pop(int(supplier_id), None)
    return write_metadata(metadata, metadata_path)


def read_keychain_password(supplier_id: int, username: str) -> str | None:
    """Read one password from macOS Keychain."""
    if not username or shutil.which("security") is None:
        return None
    cmd = [
        "security",
        "find-generic-password",
        "-s",
        keychain_service_name(supplier_id),
        "-a",
        username,
        "-w",
    ]
    completed = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    password = completed.stdout.rstrip("\n")
    return password or None


def _run_security(args: list[str], *, runner: Callable | None = None) -> subprocess.CompletedProcess:
    if runner is None:
        if shutil.which("security") is None:
            raise RuntimeError("macOS security CLI is not available")
        runner = subprocess.run
    completed = runner(
        ["security", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = getattr(completed, "stderr", "") or "security command failed"
        raise RuntimeError(detail.strip())
    return completed


def store_keychain_password(
    supplier_id: int,
    username: str,
    password: str,
    *,
    runner: Callable | None = None,
) -> None:
    if not username:
        raise ValueError("username is required")
    if not password:
        raise ValueError("password is required")
    _run_security(
        [
            "add-generic-password",
            "-U",
            "-s",
            keychain_service_name(supplier_id),
            "-a",
            username,
            "-w",
            password,
        ],
        runner=runner,
    )


def delete_keychain_password(
    supplier_id: int,
    username: str,
    *,
    runner: Callable | None = None,
) -> None:
    if not username:
        return
    _run_security(
        [
            "delete-generic-password",
            "-s",
            keychain_service_name(supplier_id),
            "-a",
            username,
        ],
        runner=runner,
    )


def load_keychain_credentials(
    supplier_ids: Iterable[int] | None = None,
    *,
    metadata_path: Path | str | None = None,
    keychain_reader: KeychainReader | None = None,
) -> dict[int, Credential]:
    metadata = load_metadata(metadata_path)
    if supplier_ids is None:
        ids = sorted(metadata)
    else:
        ids = sorted({int(sid) for sid in supplier_ids})
    reader = keychain_reader or read_keychain_password
    out: dict[int, Credential] = {}
    for sid in ids:
        entry = metadata.get(sid)
        if not entry:
            continue
        username = str(entry.get("user") or "")
        if not username:
            continue
        password = reader(sid, username)
        if not password:
            continue
        out[sid] = Credential(
            supplier_id=sid,
            url=str(entry.get("url") or ""),
            user=username,
            password=password,
            account=str(entry.get("acct") or ""),
            saved_at=str(entry.get("savedAt") or ""),
            source="keychain",
        )
    return out


def load_legacy_plaintext_vault(path: Path | str) -> dict[int, Credential]:
    """Load explicitly selected legacy JSON credentials."""
    path = Path(path).expanduser()
    if not path.exists():
        return {}
    raw = _read_json_object(path)
    out: dict[int, Credential] = {}
    for k, v in raw.items():
        try:
            sid = int(k)
        except Exception:
            continue
        if isinstance(v, dict):
            cred = Credential.from_dict(sid, v)
            cred.source = "legacy-json"
            out[sid] = cred
    return out


def load_vault(
    path: Path | str | None = None,
    *,
    supplier_ids: Iterable[int] | None = None,
    metadata_path: Path | str | None = None,
    keychain_reader: KeychainReader | None = None,
) -> dict[int, Credential]:
    """Load credentials. Returns {} when no explicit safe source is configured."""
    out = load_keychain_credentials(
        supplier_ids=supplier_ids,
        metadata_path=metadata_path,
        keychain_reader=keychain_reader,
    )

    explicit_legacy_path = path or os.environ.get(LEGACY_VAULT_PATH_ENV)
    if explicit_legacy_path:
        log.warning(
            "loading legacy plaintext credential vault from explicit path %s",
            explicit_legacy_path,
        )
        out.update(load_legacy_plaintext_vault(explicit_legacy_path))

    return out
