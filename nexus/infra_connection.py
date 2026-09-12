from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from threading import RLock
from typing import Callable, Any

from pydantic import BaseModel, Field

from nexus.infra import InfraSnapshotError, read_snapshot


HOST_PATTERN = re.compile(r'^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|\[[0-9A-Fa-f:]+\])$')
USER_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_.-]{0,63}$')
FILE_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
REMOTE_COLLECTOR = '/usr/local/bin/nexus-infra-readonly'


class InfraConnectionError(RuntimeError):
    pass


class InfraConnectionConflict(InfraConnectionError):
    pass


class InfraConnectionPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(min_length=1, max_length=64)
    identity_file: str = Field(min_length=1, max_length=128)
    revision: int = Field(default=0, ge=0)


def _approved_file(root: Path, filename: str) -> Path:
    if not FILE_PATTERN.fullmatch(filename):
        raise InfraConnectionError('Use only an approved SSH key filename, not a path.')
    candidate = root / filename
    try:
        resolved_root, resolved = root.resolve(strict=True), candidate.resolve(strict=True)
    except OSError as error:
        raise InfraConnectionError('The approved SSH identity file is unavailable.') from error
    if resolved.parent != resolved_root or candidate.is_symlink() or not resolved.is_file():
        raise InfraConnectionError('The SSH identity file must be a regular file in the approved key directory.')
    return resolved


def collect_remote_infra(settings: InfraConnectionPayload, mode: str, *, key_root: Path, known_hosts: Path):
    if mode not in {'snapshot', 'live'}:
        raise InfraConnectionError('Unsupported infrastructure source mode.')
    identity = _approved_file(key_root, settings.identity_file)
    if not known_hosts.is_file():
        raise InfraConnectionError('The managed SSH known_hosts file is unavailable.')
    target = f'{settings.username}@{settings.host}'
    command = [
        'ssh', '-F', os.devnull, '-i', str(identity), '-p', str(settings.port),
        '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
        '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={known_hosts}',
        '-o', 'ConnectTimeout=6', '-o', 'ConnectionAttempts=1',
        target, REMOTE_COLLECTOR, mode,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise InfraConnectionError('The remote server did not return infrastructure data in time.') from error
    if result.returncode:
        raise InfraConnectionError('The remote read-only collector could not be reached or rejected access.')
    if len(result.stdout) > 100_000:
        raise InfraConnectionError('The remote infrastructure response exceeded the safety limit.')
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise InfraConnectionError('The remote collector returned invalid data.') from error
    if not isinstance(value, dict) or not value.get('generated_at'):
        raise InfraConnectionError('The remote collector returned incomplete data.')
    return value


class InfraConnections:
    def __init__(self, path: Path, *, local_snapshot_path: str,
                 local_live_collector: Callable[[], dict[str, Any]], key_root: Path,
                 known_hosts: Path):
        self.path = path
        self.local_snapshot_path = local_snapshot_path
        self.local_live_collector = local_live_collector
        self.key_root = key_root
        self.known_hosts = known_hosts
        self.remote_collector = lambda settings, mode: collect_remote_infra(
            settings, mode, key_root=self.key_root, known_hosts=self.known_hosts)
        self.bound_count = lambda connection_id: 0
        self.lock = RLock()

    def _read(self):
        if not self.path.exists():
            return {'profiles': {}}
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            raise InfraConnectionError('Infrastructure connection settings cannot be read. Restore their backup.') from error
        return value if isinstance(value, dict) else {'profiles': {}}

    def _write(self, document):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.infra-connections-', dir=self.path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
                json.dump(document, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    @staticmethod
    def _validate(payload):
        if not payload.name.strip():
            raise InfraConnectionError('A server connection name is required.')
        if not HOST_PATTERN.fullmatch(payload.host) or not USER_PATTERN.fullmatch(payload.username):
            raise InfraConnectionError('Enter a valid server host and SSH username.')
        if not FILE_PATTERN.fullmatch(payload.identity_file):
            raise InfraConnectionError('Use only an approved SSH key filename, not a path.')

    @staticmethod
    def _public(connection_id, profile):
        return {'id': connection_id, **profile}

    def profiles(self):
        with self.lock:
            return [self._public(key, value) for key, value in self._read().get('profiles', {}).items()]

    def choices(self, *, admin):
        choices = [{'id': 'local', 'name': 'Local Nexus server', 'kind': 'local'}]
        if admin:
            choices.extend({'id': p['id'], 'name': p['name'], 'kind': 'ssh'} for p in self.profiles())
        return choices

    def _draft(self, payload, connection_id=None):
        self._validate(payload)
        profiles = self._read().get('profiles', {})
        current = profiles.get(connection_id) if connection_id else None
        if connection_id and not current:
            raise InfraConnectionError('Infrastructure server connection no longer exists.')
        expected = current['revision'] if current else 0
        if payload.revision != expected:
            raise InfraConnectionConflict('Server connection changed. Reload it before saving.')
        if connection_id and self.bound_count(connection_id) and any(
            current[key] != getattr(payload, key) for key in ('host', 'port', 'username')
        ):
            raise InfraConnectionConflict('Existing chats use this server. Create a new connection for another endpoint.')
        return payload

    def test(self, payload, connection_id=None, mode='live'):
        with self.lock:
            draft = self._draft(payload, connection_id)
        return self.remote_collector(draft, mode)

    def save(self, payload, connection_id=None):
        self.test(payload, connection_id, 'live')
        with self.lock:
            self._draft(payload, connection_id)
            document = self._read()
            profiles = document.setdefault('profiles', {})
            if not connection_id and len(profiles) >= 20:
                raise InfraConnectionError('Maximum 20 saved server connections.')
            if any(p['name'].casefold() == payload.name.strip().casefold()
                   for key, p in profiles.items() if key != connection_id):
                raise InfraConnectionConflict('A server connection with this name already exists.')
            connection_id = connection_id or uuid.uuid4().hex
            value = payload.model_dump()
            value['name'] = value['name'].strip()
            value['revision'] += 1
            profiles[connection_id] = value
            self._write(document)
            return self._public(connection_id, value)

    def delete(self, connection_id, revision):
        with self.lock:
            document = self._read()
            profile = document.get('profiles', {}).get(connection_id)
            if not profile:
                raise InfraConnectionError('Infrastructure server connection no longer exists.')
            if profile['revision'] != revision or self.bound_count(connection_id):
                raise InfraConnectionConflict('Connection changed or is still used by chats.')
            del document['profiles'][connection_id]
            self._write(document)

    def collect(self, connection_id, mode):
        if connection_id == 'local':
            return self.local_live_collector() if mode == 'live' else read_snapshot(self.local_snapshot_path)
        with self.lock:
            profile = self._read().get('profiles', {}).get(connection_id)
            if not profile:
                raise InfraConnectionError('Infrastructure server connection is unavailable. No fallback was used.')
            settings = InfraConnectionPayload(**profile)
        return self.remote_collector(settings, mode)

    def server_label(self, connection_id):
        if connection_id == 'local':
            return 'Local Nexus server'
        with self.lock:
            profile = self._read().get('profiles', {}).get(connection_id)
            if not profile:
                raise InfraConnectionError('Infrastructure server connection is unavailable. No fallback was used.')
            return profile['host']
