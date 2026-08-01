from __future__ import annotations

import json
import sys
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATABASE = ROOT / "artifacts" / "ui-admin-smoke.sqlite3"
SNAPSHOT = ROOT / "artifacts" / "ui-infra-snapshot.json"
SYNTHETIC_DATABASE = ROOT / "artifacts" / "ui-synthetic-business.sqlite3"


def build_app():
    if DATABASE.exists():
        DATABASE.unlink()
    SNAPSHOT.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-24T12:00:00+00:00",
                "hostname": "ui-test-vps",
                "memory": {"used_mb": 2048, "total_mb": 8192},
                "services": [{"name": "nexuschat", "active": True}],
                "scope": "sanitized_read_only",
            }
        ),
        encoding="utf-8",
    )
    from conftest import FakeAI, FakeModelCatalog
    from nexus.app import create_app

    def collect_live_infra():
        return {
            "generated_at": "2026-07-26T14:30:00+00:00",
            "hostname": "ui-live-vps",
            "memory": {"used_mb": 2304, "total_mb": 8192},
            "services": [{"name": "nexuschat", "active": True}],
            "scope": "sanitized_read_only",
            "collection_mode": "live",
        }

    app = create_app(
        database_path=str(DATABASE),
        ai_provider=FakeAI(),
        model_catalog=FakeModelCatalog(),
        infra_snapshot_path=str(SNAPSHOT),
        live_infra_collector=collect_live_infra,
        synthetic_database_path=str(SYNTHETIC_DATABASE),
        secure_cookies=False,
    )

    app.state.store.create_user(
        name="UI Admin",
        email="ui-admin@example.test",
        password="UiAdminPass!2026",
        role="admin",
    )
    return app


def main() -> None:
    app = build_app()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
