"""Manage local scraper credentials without storing passwords in the dashboard."""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from .core import vault


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
