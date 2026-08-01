from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SERVICES = (
    "nexuschat.service",
    "nginx.service",
    "grafana-server.service",
)
HEALTH_ENDPOINTS = {
    "nexuschat": "http://127.0.0.1:8300/health",
}


class InfraSnapshotError(RuntimeError):
    pass


def _run(
    *command: str,
    timeout: int = 4,
    input_text: str | None = None,
) -> tuple[int, str]:
    """Run one fixed read-only command without invoking a shell."""
    try:
        result = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout.strip()[:100_000]
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def _memory() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        lines = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"total_mb": 0, "used_mb": 0, "available_mb": 0}
    for line in lines:
        key, raw = line.split(":", 1)
        values[key] = int(raw.strip().split()[0])
    total = values.get("MemTotal", 0) // 1024
    available = values.get("MemAvailable", 0) // 1024
    return {
        "total_mb": total,
        "used_mb": max(0, total - available),
        "available_mb": available,
    }


def _system() -> dict[str, float | int]:
    try:
        one, five, fifteen = os.getloadavg()
        uptime_seconds = int(
            float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
        )
    except (AttributeError, OSError, ValueError):
        one = five = fifteen = 0.0
        uptime_seconds = 0
    return {
        "cpu_count": os.cpu_count() or 0,
        "load_1m": round(one, 2),
        "load_5m": round(five, 2),
        "load_15m": round(fifteen, 2),
        "uptime_seconds": uptime_seconds,
    }


def _disk() -> dict[str, int]:
    usage = shutil.disk_usage("/")
    return {
        "total_gb": round(usage.total / 1024**3),
        "used_gb": round(usage.used / 1024**3),
        "free_gb": round(usage.free / 1024**3),
        "used_percent": round(usage.used * 100 / usage.total),
    }


def _services() -> list[dict[str, str | bool]]:
    result = []
    for name in SERVICES:
        code, state = _run("systemctl", "is-active", name)
        result.append(
            {
                "name": name.removesuffix(".service"),
                "active": code == 0 and state == "active",
                "state": state or "unknown",
            }
        )
    return result


def _listening_ports() -> list[int]:
    _, output = _run("ss", "-lntH")
    ports: set[int] = set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        try:
            ports.add(int(fields[3].rsplit(":", 1)[1]))
        except (IndexError, ValueError):
            continue
    return sorted(ports)


def _health() -> list[dict[str, str | bool]]:
    result = []
    for name, url in HEALTH_ENDPOINTS.items():
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                ok = 200 <= response.status < 300
                status = str(response.status)
        except Exception:
            ok = False
            status = "unreachable"
        result.append({"name": name, "healthy": ok, "status": status})
    return result


def _tls() -> dict[str, str | bool]:
    code, certificate = _run(
        "openssl",
        "s_client",
        "-servername",
        "raizenko.cloud",
        "-connect",
        "127.0.0.1:443",
        timeout=5,
        input_text="",
    )
    if code != 0 or not certificate:
        return {"valid": False, "expires": "unknown"}
    code, output = _run(
        "openssl",
        "x509",
        "-noout",
        "-enddate",
        timeout=3,
        input_text=certificate,
    )
    expiry = output.removeprefix("notAfter=").strip()
    return {"valid": code == 0 and bool(expiry), "expires": expiry or "unknown"}


def _nginx_config() -> dict[str, str | bool | None]:
    code, _ = _run("nginx", "-t")
    return {
        "valid": True if code == 0 else None,
        "status": "ok" if code == 0 else "unavailable",
    }


def collect_infra_state(
    collection_mode: str = "live",
) -> dict[str, Any]:
    """Collect a bounded, sanitized server view using fixed read-only checks."""
    if collection_mode not in {"live", "snapshot"}:
        raise ValueError("Unsupported infrastructure collection mode.")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "system": _system(),
        "memory": _memory(),
        "disk_root": _disk(),
        "services": _services(),
        "health": _health(),
        "listening_tcp_ports": _listening_ports(),
        "tls_raizenko_cloud": _tls(),
        "nginx_config": _nginx_config(),
        "scope": "sanitized_read_only",
        "collection_mode": collection_mode,
    }


def read_snapshot(path: str) -> dict[str, Any]:
    snapshot_path = Path(path)
    try:
        raw = snapshot_path.read_text(encoding="utf-8")
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as error:
        raise InfraSnapshotError(
            "Infra snapshot zatiaľ nie je dostupný. Skús to o chvíľu."
        ) from error
    if not isinstance(value, dict) or not value.get("generated_at"):
        raise InfraSnapshotError("Infra snapshot nemá platný formát.")
    return value


def infra_prompt(
    snapshot: dict[str, Any],
    source_mode: str = "snapshot",
) -> str:
    prompt_snapshot = {**snapshot, "collection_mode": source_mode}
    serialized = json.dumps(prompt_snapshot, ensure_ascii=False, sort_keys=True)
    source_description = (
        "živého merania vykonaného pri tejto požiadavke"
        if source_mode == "live"
        else "posledného uloženého snapshotu"
    )
    return (
        "INFRA AGENT / READ-ONLY\n"
        "Odpovedaj iba na infraštruktúrne, systémové a aplikačné otázky o tomto "
        f"serveri. Údaje pochádzajú zo {source_description}. "
        "Použi výhradne priložené sanitizované údaje a prípadný KB "
        "kontext. Nikdy netvrď, že si spustil príkaz, vykonal zmenu alebo vidíš "
        "údaj, ktorý v snapshote nie je. Ak údaj chýba, povedz to. V každej "
        "odpovedi uveď čas snapshotu. Neodhaľuj ani nehádaj heslá, tokeny, "
        "premenné prostredia či tajomstvá.\n\n"
        f"SERVER SNAPSHOT:\n{serialized}"
    )
