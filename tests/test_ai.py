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

