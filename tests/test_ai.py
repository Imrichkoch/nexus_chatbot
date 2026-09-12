from types import SimpleNamespace

import nexus.ai as ai_module


def test_openrouter_uses_chat_completions(monkeypatch):
    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls["payload"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="OpenRouter odpoveď")
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=21, completion_tokens=8),
            )

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(ai_module, "OpenAI", FakeClient)
    provider = ai_module.OpenAIProvider(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
    )
    result = provider.reply(
        messages=[{"role": "user", "content": "Ahoj"}],
        user_id=42,
        model="openai/gpt-5.4-mini",
        system_prompt="Odpovedaj po slovensky.",
    )

    assert calls["client"]["base_url"] == "https://openrouter.ai/api/v1"
    assert calls["payload"]["messages"][0]["role"] == "system"
    assert result["text"] == "OpenRouter odpoveď"
    assert result["input_tokens"] == 21
    assert result["output_tokens"] == 8


def test_direct_openai_uses_responses_api(monkeypatch):
    calls = {}

    class FakeResponses:
        def create(self, **kwargs):
            calls["payload"] = kwargs
            return SimpleNamespace(
                output_text="Responses odpoveď",
                usage=SimpleNamespace(input_tokens=13, output_tokens=5),
            )

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.responses = FakeResponses()

    monkeypatch.setattr(ai_module, "OpenAI", FakeClient)
    provider = ai_module.OpenAIProvider(api_key="test-key", base_url="")
    result = provider.reply(
        messages=[{"role": "user", "content": "Ahoj"}],
        user_id=42,
        model="gpt-5.6-terra",
        system_prompt="Odpovedaj po slovensky.",
    )

    assert "base_url" not in calls["client"]
    assert calls["payload"]["model"] == "gpt-5.6-terra"
    assert result["text"] == "Responses odpoveď"


def test_openrouter_stream_yields_text_and_usage(monkeypatch):
    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls["payload"] = kwargs
            return iter(
                [
                    SimpleNamespace(
                        choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello "))],
                        usage=None,
                    ),
                    SimpleNamespace(
                        choices=[SimpleNamespace(delta=SimpleNamespace(content="world"))],
                        usage=None,
                    ),
                    SimpleNamespace(
                        choices=[],
                        usage=SimpleNamespace(prompt_tokens=31, completion_tokens=2),
                    ),
                ]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(ai_module, "OpenAI", FakeClient)
    provider = ai_module.OpenAIProvider(
        api_key="test-key", base_url="https://openrouter.ai/api/v1"
    )

    events = list(
        provider.stream_reply(
            messages=[{"role": "user", "content": "Hello"}],
            user_id=42,
            model="openai/gpt-5.6-luna",
            system_prompt="Answer clearly.",
        )
    )

    assert calls["payload"]["stream"] is True
    assert calls["payload"]["stream_options"] == {"include_usage": True}
    assert "".join(event.get("content", "") for event in events) == "Hello world"
    assert events[-1]["input_tokens"] == 31


def test_direct_openai_stream_yields_text_and_usage(monkeypatch):
    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def __iter__(self):
            return iter(
                [
                    SimpleNamespace(type="response.output_text.delta", delta="Direct "),
                    SimpleNamespace(type="response.output_text.delta", delta="stream"),
                ]
            )

        def get_final_response(self):
            return SimpleNamespace(
                usage=SimpleNamespace(input_tokens=19, output_tokens=2)
            )

    class FakeResponses:
        def stream(self, **kwargs):
            return FakeStream()

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr(ai_module, "OpenAI", FakeClient)
    provider = ai_module.OpenAIProvider(api_key="test-key", base_url="")

    events = list(
        provider.stream_reply(
            messages=[{"role": "user", "content": "Hello"}],
            user_id=42,
            model="gpt-5.6-terra",
            system_prompt="Answer clearly.",
        )
    )

    assert "".join(event.get("content", "") for event in events) == "Direct stream"
    assert events[-1]["input_tokens"] == 19


def test_sql_report_preserves_original_language_and_admin_instructions(monkeypatch):
    captured = {}
    provider = ai_module.OpenAIProvider(api_key="test-key", base_url="")

    def fake_reply(**kwargs):
        captured.update(kwargs)
        return {"text": "REPORT / TOP SALES REPRESENTATIVE", "model": kwargs["model"]}

    monkeypatch.setattr(provider, "reply", fake_reply)
    provider.create_sql_report(
        question="Which sales representative generated the highest revenue?",
        sql="SELECT sales_rep, SUM(total) FROM sales GROUP BY sales_rep",
        query_result={"rows": [{"sales_rep": "Peter Malik", "total": 284495.35}]},
        user_id=42,
        model="gpt-5.6-terra",
        admin_system_prompt="Always answer in English.",
    )

    assert "Always answer in English." in captured["system_prompt"]
    assert "ORIGINAL USER REQUEST" in captured["system_prompt"]
    assert "same language as the original user request" in captured["system_prompt"]
    assert "Original user request:" in captured["messages"][0]["content"]
    assert "Požiadavka:" not in captured["messages"][0]["content"]


def test_sql_planner_resolves_relative_dates_without_sql_functions(monkeypatch):
    captured = {}
    provider = ai_module.OpenAIProvider(api_key="test-key", base_url="")

    def fake_reply(**kwargs):
        captured.update(kwargs)
        return {
            "text": (
                "SELECT * FROM invoices WHERE issued_on >= '2026-01-01' "
                "AND issued_on < '2027-01-01'"
            )
        }

    monkeypatch.setattr(provider, "reply", fake_reply)
    monkeypatch.setattr(ai_module, "sql_planning_date", lambda: "2026-09-12")

    provider.generate_sql(
        question="vyhladaj mi faktury za tento rok",
        schema="SQL dialect: sqlite.\nTABLE invoices (issued_on TEXT)",
        user_id=42,
        model="gpt-5.6-terra",
    )

    prompt = captured["system_prompt"]
    assert "Current date: 2026-09-12" in prompt
    assert "half-open literal date ranges" in prompt
    assert "Do not use SQL date/time functions" in prompt

