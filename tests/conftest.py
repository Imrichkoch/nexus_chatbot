import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class FakeAI:
    def __init__(self):
        self.calls = []
        self.sql_calls = []
        self.report_calls = []

    def reply(self, *, messages, user_id, model, system_prompt):
        self.calls.append(
            {
                "messages": messages,
                "user_id": user_id,
                "model": model,
                "system_prompt": system_prompt,
            }
        )
        return {
            "text": "Testovacia odpoveď z Nexus AI.",
            "model": model,
            "input_tokens": 12,
            "output_tokens": 7,
        }

    def generate_sql(
        self, *, question, schema, user_id, model, error_context=None
    ):
        self.sql_calls.append(
            {
                "question": question,
                "schema": schema,
                "user_id": user_id,
                "model": model,
                "error_context": error_context,
            }
        )
        return {
            "sql": (
                "SELECT c.country, ROUND(SUM(oi.quantity * oi.unit_price), 2) "
                "AS revenue FROM customers c JOIN orders o ON o.customer_id = c.id "
                "JOIN order_items oi ON oi.order_id = o.id "
                "GROUP BY c.country ORDER BY revenue DESC"
            ),
            "input_tokens": 20,
            "output_tokens": 14,
        }

    def create_sql_report(
        self, *, question, sql, query_result, user_id, model, admin_system_prompt
    ):
        self.report_calls.append(
            {
                "question": question,
                "sql": sql,
                "query_result": query_result,
                "user_id": user_id,
                "model": model,
                "admin_system_prompt": admin_system_prompt,
            }
        )
        return {
            "text": (
                "REPORT / TRŽBY PODĽA KRAJÍN\n\n"
                "Zhrnutie\nFiktívne dáta ukazujú poradie krajín podľa tržieb."
            ),
            "model": model,
            "input_tokens": 30,
            "output_tokens": 22,
        }


class FakeModelCatalog:
    def list_models(self):
        return [
            {
                "id": "openai/gpt-5.6-terra",
                "name": "OpenAI: GPT-5.6 Terra",
                "context_length": 400000,
                "prompt_price": "0.000001",
                "completion_price": "0.000004",
            },
            {
                "id": "anthropic/claude-sonnet-4.5",
                "name": "Anthropic: Claude Sonnet 4.5",
                "context_length": 200000,
                "prompt_price": "0.000003",
                "completion_price": "0.000015",
            },
        ]


@pytest.fixture
def app(tmp_path):
    from nexus.app import create_app

    fake_ai = FakeAI()
    application = create_app(
        database_path=str(tmp_path / "test.sqlite3"),
        ai_provider=fake_ai,
        model_catalog=FakeModelCatalog(),
        infra_snapshot_path=str(tmp_path / "infra-snapshot.json"),
        synthetic_database_path=str(tmp_path / "synthetic-business.sqlite3"),
        secure_cookies=False,
    )
    application.state.fake_ai = fake_ai
    application.state.store.create_user(
        name="Nexus Admin",
        email="admin@example.test",
        password="AdminPass!2026",
        role="admin",
    )
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def register(client, email="user@example.test", password="UserPass!2026"):
    return client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": password},
    )


def login(client, email="user@example.test", password="UserPass!2026"):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
