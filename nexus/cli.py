from __future__ import annotations

import argparse
import sqlite3
import getpass

from nexus.store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="NexusChat administration")
    parser.add_argument(
        "--database",
        default="/opt/nexuschat/data/nexus.sqlite3",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_admin = subparsers.add_parser("create-admin")
    create_admin.add_argument("--name", required=True)
    create_admin.add_argument("--email", required=True)
    create_admin.add_argument("--password", help='Prefer the interactive prompt to avoid shell history.')
    create_user = subparsers.add_parser("create-user")
    create_user.add_argument("--name", required=True)
    create_user.add_argument("--email", required=True)
    create_user.add_argument("--password", help='Prefer the interactive prompt to avoid shell history.')
    args = parser.parse_args()
    password = args.password or getpass.getpass('Password: ')
    if not (10 <= len(password) and len(password.encode('utf-8')) <= 72
            and any(c.islower() for c in password) and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)):
        raise SystemExit('Password requires 10+ characters, upper/lower case, a digit and at most 72 UTF-8 bytes.')

    store = Store(args.database)
    role = "admin" if args.command == "create-admin" else "user"
    try:
        user = store.create_user(
            name=args.name,
            email=args.email,
            password=password,
            role=role,
        )
    except sqlite3.IntegrityError:
        raise SystemExit(f"User {args.email} already exists")
    print(f"Created {user['role']} account: {user['email']}")


if __name__ == "__main__":
    main()

