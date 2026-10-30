"""Verified SQLite backup and restore to a new destination; never overwrites data."""
from __future__ import annotations

import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def copy_database(source: Path, destination: Path, *, revoke_sessions=False):
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if source == destination:
        raise ValueError('Source and destination must differ.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement, including an existing WAL DB.
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
            with closing(sqlite3.connect(destination)) as copied:
                original.backup(copied)
                if copied.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Database integrity check failed.')
                if copied.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('Database foreign key check failed.')
                if revoke_sessions and copied.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'"
                ).fetchone():
                    copied.execute('DELETE FROM sessions')
                copied.commit()
        return destination
    except Exception:
        # Keep the failed copy for diagnosis; the source is never modified.
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['backup', 'restore'])
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    output = copy_database(args.source, args.destination,
                           revoke_sessions=args.operation == 'restore')
    print(f'Verified {args.operation}: {output}')


if __name__ == '__main__':
    main()
