from __future__ import annotations

import argparse
import sqlite3

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
    create_admin.add_argument("--password", required=True)
    create_user = subparsers.add_parser("create-user")
    create_user.add_argument("--name", required=True)
    create_user.add_argument("--email", required=True)
    create_user.add_argument("--password", required=True)
    args = parser.parse_args()

    store = Store(args.database)
    role = "admin" if args.command == "create-admin" else "user"
    try:
        user = store.create_user(
            name=args.name,
            email=args.email,
            password=args.password,
            role=role,
        )
    except sqlite3.IntegrityError:
        raise SystemExit(f"User {args.email} already exists")
    print(f"Created {user['role']} account: {user['email']}")


if __name__ == "__main__":
    main()

