"""Manage local scraper credentials without storing passwords in the dashboard."""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from .core import vault
from . import manual_login


def _add_metadata_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=None,
        help="override the non-secret credential metadata JSON path",
    )


def _read_password_from_args(args: argparse.Namespace) -> str:
    if args.password_stdin:
        return sys.stdin.read().rstrip("\n")
    return getpass.getpass("Supplier password: ")


def _set(args: argparse.Namespace) -> int:
    password = _read_password_from_args(args)
    if not password:
        raise SystemExit("password is required")
    vault.save_metadata_entry(
        args.id,
        url=args.url,
        user=args.user,
        account=args.account or "",
        metadata_path=args.metadata_path,
    )
    vault.store_keychain_password(args.id, args.user, password)
    print(f"stored credential metadata and keychain password for supplier #{args.id}")
    return 0


def _list(args: argparse.Namespace) -> int:
    metadata = vault.load_metadata(args.metadata_path)
    creds = vault.load_vault(
        supplier_ids=metadata.keys(),
        metadata_path=args.metadata_path,
    )
    if not metadata:
        print("no credential metadata configured")
        return 0
    for sid in sorted(metadata):
        entry = metadata[sid]
        has_password = "yes" if sid in creds else "no"
        user = entry.get("user", "")
        url = entry.get("url", "")
        print(f"#{sid} user={user} keychain_password={has_password} url={url}")
    return 0


def _delete(args: argparse.Namespace) -> int:
    metadata = vault.load_metadata(args.metadata_path)
    entry = metadata.get(args.id, {})
    username = entry.get("user", "")
    if username:
        vault.delete_keychain_password(args.id, username)
    vault.delete_metadata_entry(args.id, metadata_path=args.metadata_path)
    print(f"deleted credential metadata for supplier #{args.id}")
    return 0


def _login_session(args: argparse.Namespace) -> int:
    metadata = vault.load_metadata(args.metadata_path)
    entry = metadata.get(args.id)
    login_url = args.url or (entry or {}).get("url", "")
    creds = vault.load_vault(
        supplier_ids=[args.id],
        metadata_path=args.metadata_path,
    )
    credential = creds.get(args.id)
    if credential is None:
        raise SystemExit(
            f"no Keychain-backed credential found for supplier #{args.id}; "
            "run `python3 -m scrape.credentials set ...` first"
        )
    if not login_url:
        raise SystemExit(
            f"no login URL found for supplier #{args.id}; pass --url or save metadata first"
        )

    result = manual_login.capture_manual_login_session(
        supplier_id=args.id,
        credential=credential,
        login_url=login_url,
        success_texts=args.success_text,
        success_url_contains=args.success_url_contains,
        timeout_seconds=args.timeout,
        headed=not args.headless,
    )
    if result.success:
        print(
            f"saved Playwright storage state for supplier #{args.id} "
            f"to {result.storage_state_path}"
        )
        print(f"success signals: {', '.join(result.reasons)}")
        return 0
    print(f"manual login session was not saved: {', '.join(result.reasons)}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage BloomBox scraper credentials in the local OS store.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="store one supplier credential")
    _add_metadata_arg(set_parser)
    set_parser.add_argument("--id", type=int, required=True)
    set_parser.add_argument("--url", required=True)
    set_parser.add_argument("--user", required=True)
    set_parser.add_argument("--account", default="")
    set_parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="read the supplier password from stdin instead of prompting",
    )
    set_parser.set_defaults(func=_set)

    list_parser = subparsers.add_parser("list", help="list configured suppliers")
    _add_metadata_arg(list_parser)
    list_parser.set_defaults(func=_list)

    delete_parser = subparsers.add_parser("delete", help="delete one supplier credential")
    _add_metadata_arg(delete_parser)
    delete_parser.add_argument("--id", type=int, required=True)
    delete_parser.set_defaults(func=_delete)

    session_parser = subparsers.add_parser(
        "login-session",
        help="open a headed browser for manual supplier login and save session state",
    )
    _add_metadata_arg(session_parser)
    session_parser.add_argument("--id", type=int, required=True)
    session_parser.add_argument(
        "--url",
        default="",
        help="override login URL; defaults to saved credential metadata URL",
    )
    session_parser.add_argument(
        "--success-text",
        action="append",
        default=[],
        help="case-insensitive page text that indicates a successful login",
    )
    session_parser.add_argument(
        "--success-url-contains",
        action="append",
        default=[],
        help="case-insensitive URL substring that indicates a successful login",
    )
    session_parser.add_argument("--timeout", type=int, default=600)
    session_parser.add_argument(
        "--headless",
        action="store_true",
        help="run without showing the browser; not useful for CAPTCHA handoff",
    )
    session_parser.set_defaults(func=_login_session)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
