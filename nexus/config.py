"""Deployment configuration; no credentials are exposed through public config."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, '1' if default else '0').lower()
    if value not in {'0', '1', 'true', 'false'}:
        raise ValueError(f'{name} must be 0 or 1')
    return value in {'1', 'true'}


@dataclass(frozen=True)
class RuntimeConfig:
    allowed_hosts: list[str]
    base_path: str
    registration_enabled: bool
    session_hours: int

    @classmethod
    def from_env(cls, *, secure_cookies: bool):
        hosts = [host.strip() for host in os.getenv(
            'NEXUS_ALLOWED_HOSTS',
            'raizenko.cloud,www.raizenko.cloud,127.0.0.1,localhost,testserver',
        ).split(',') if host.strip()]
        if not hosts or any('/' in host or host == '*' for host in hosts):
            raise ValueError('NEXUS_ALLOWED_HOSTS requires explicit hostnames')
        path = os.getenv('NEXUS_BASE_PATH', '/nexus' if secure_cookies else '').rstrip('/')
        if path and (not re.fullmatch(r'/[a-zA-Z0-9_/-]+', path) or '//' in path):
            raise ValueError('NEXUS_BASE_PATH must be empty or an absolute URL path')
        hours = int(os.getenv('NEXUS_SESSION_HOURS', '168'))
        if not 1 <= hours <= 168:
            raise ValueError('NEXUS_SESSION_HOURS must be between 1 and 168')
        return cls(hosts, path, env_bool('NEXUS_REGISTRATION_ENABLED', True), hours)
