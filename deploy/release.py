#!/usr/bin/env python3
"""Single-host systemd release: staged dependencies, backups, code+venv rollback.

Run as root during a maintenance window. Database rollback is deliberately manual
because traffic may have written new data after service startup.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import subprocess
import tarfile
import time
import urllib.request
from datetime import datetime, timezone


def unpack(archive: Path, target: Path):
    allowed = {'nexus', 'deploy', 'docs', 'requirements.txt', 'README.md', '.env.example',
               'Dockerfile', 'compose.yaml', '.dockerignore'}
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        if sum(member.size for member in members) > 100 * 1024 * 1024:
            raise ValueError('Release archive is too large')
        for member in members:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts or '\\' in member.name
                    or not path.parts or path.parts[0] not in allowed
                    or not (member.isfile() or member.isdir())):
                raise ValueError('Release contains an unsafe or unexpected member')
        bundle.extractall(target, filter='data')
    if not (target / 'nexus/app.py').is_file() or not (target / 'requirements.txt').is_file():
        raise ValueError('Incomplete release')


def run(*arguments, **kwargs):
    subprocess.run(arguments, check=True, **kwargs)


def ready():
    for _ in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8300/ready', timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(1)
    raise RuntimeError('Readiness check failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--app-root', type=Path, default=Path('/opt/nexuschat'))
    args = parser.parse_args()
    root = args.app_root.resolve(strict=True)
    if len(root.parts) < 3 or not (root / 'nexus/app.py').is_file():
        raise SystemExit('Expected an existing, dedicated NexusChat application directory')
    archive = args.archive.resolve(strict=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    release_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + digest[:12]
    release = root / '.releases' / release_id
    release.mkdir(parents=True, exist_ok=False)
    os.chmod(release, 0o755)
    unpack(archive, release)
    run('python3', '-m', 'venv', str(release / 'venv'))
    python = str(release / 'venv/bin/python')
    run(python, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(release / 'requirements.txt'))
    run(python, '-m', 'pip', 'check')
    run(python, '-m', 'compileall', '-q', str(release / 'nexus'))
    # Check startup without opening live databases or sending provider requests.
    run(python, '-c', "from nexus.app import create_app; create_app(database_path='preflight.sqlite3', synthetic_database_path='preflight-data.sqlite3')",
        cwd=release)
    backup = release / 'backup'
    backup.mkdir(mode=0o700)
    switched_code = switched_venv = False
    run('systemctl', 'stop', 'nexuschat.service')
    try:
        for filename in ('nexus.sqlite3', 'synthetic-business.sqlite3'):
            source = root / 'data' / filename
            if source.exists():
                with sqlite3.connect(source) as db, sqlite3.connect(backup / filename) as copied:
                    db.backup(copied)
                    if copied.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise RuntimeError('Backup integrity check failed')
                os.chmod(backup / filename, 0o600)
        for secret_name in ('ldap-bind-password', 'database-connection.json'):
            secret = root / 'data' / secret_name
            if secret.exists():
                shutil.copy2(secret, backup / secret.name)
                os.chmod(backup / secret.name, 0o600)
        (root / 'nexus').rename(release / 'previous-nexus')
        switched_code = True
        (release / 'nexus').rename(root / 'nexus')
        (root / '.venv').rename(release / 'previous-venv')
        switched_venv = True
        (root / '.venv').symlink_to(release / 'venv', target_is_directory=True)
        run('systemctl', 'start', 'nexuschat.service')
        ready()
    except Exception:
        run('systemctl', 'stop', 'nexuschat.service')
        if switched_venv:
            if (root / '.venv').is_symlink():
                (root / '.venv').unlink()
            (release / 'previous-venv').rename(root / '.venv')
        if switched_code:
            if (root / 'nexus').exists():
                (root / 'nexus').rename(release / 'failed-nexus')
            (release / 'previous-nexus').rename(root / 'nexus')
        run('systemctl', 'start', 'nexuschat.service')
        raise
    for folder in ('docs', 'deploy'):
        if (release / folder).exists():
            shutil.copytree(release / folder, root / folder, dirs_exist_ok=True)
    for filename in ('requirements.txt', 'README.md'):
        shutil.copy2(release / filename, root / filename)
    print(f'Release ready: {release_id}\nSHA256: {digest}\nRecovery directory: {release}')


if __name__ == '__main__':
    main()
