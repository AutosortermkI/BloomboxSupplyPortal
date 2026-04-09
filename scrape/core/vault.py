"""
Credential vault reader.

The dashboard's Supplier Portal tab exports a JSON file of credentials
(`bloombox_vault_YYYY-MM-DD.json`) whose shape is:

    {
      "<supplier_id>": {
        "url":   "https://...",
        "user":  "buyer@bloombox.com",
        "pass":  "secret",
        "acct":  "optional account #",
        "savedAt": "2026-04-09T..."
      },
      ...
    }

This module loads the most recent vault export from a sensible default
location (or a caller-supplied path), so adapters that need login can
simply do:

    from scrape.core.vault import load_vault
    creds = load_vault().get(supplier_id)

Secrets never leave the local machine — there's no sync/upload.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_SEARCH_PATHS = [
    Path.home() / "Downloads",
    Path.home() / "BloomboxSupplyPortal" / "scrape" / "vault",
    Path(__file__).resolve().parents[1] / "vault",
]


@dataclass
class Credential:
    supplier_id: int
    url: str
    user: str
    password: str
    account: str = ""
    saved_at: str = ""

    @classmethod
    def from_dict(cls, sid: int, d: dict) -> "Credential":
        return cls(
            supplier_id=sid,
            url=d.get("url", ""),
            user=d.get("user", ""),
            password=d.get("pass", ""),
            account=d.get("acct", ""),
            saved_at=d.get("savedAt", ""),
        )


def _find_latest_vault() -> Optional[Path]:
    override = os.environ.get("BLOOMBOX_VAULT_PATH")
    if override and Path(override).exists():
        return Path(override)
    candidates: list[Path] = []
    for base in DEFAULT_SEARCH_PATHS:
        if not base.exists():
            continue
        candidates.extend(base.glob("bloombox_vault_*.json"))
        candidates.extend(base.glob("vault.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_vault(path: Path | str | None = None) -> dict[int, Credential]:
    """Load credentials from a JSON vault. Returns {} if none found."""
    if path is None:
        path = _find_latest_vault()
    if path is None:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except Exception:
        return {}
    out: dict[int, Credential] = {}
    for k, v in raw.items():
        try:
            sid = int(k)
        except Exception:
            continue
        if isinstance(v, dict):
            out[sid] = Credential.from_dict(sid, v)
    return out
