from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

from openai import OpenAI


class AIUnavailable(RuntimeError):
    pass


class OpenAIProvider:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (
            base_url if base_url is not None else os.getenv("OPENAI_BASE_URL", "")
        ).rstrip("/")

    def reply(
        self,
        *,
        messages: list[dict[str, str]],
        user_id: int,
        model: str,
        system_prompt: str,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise AIUnavailable("OpenAI API kľúč nie je nakonfigurovaný.")

        if self.base_url:
            return self._chat_completions_reply(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
            )
        return self._responses_reply(
            messages=messages,
            user_id=user_id,
            model=model,
            system_prompt=system_prompt,
        )

    def generate_sql(
        self,
        *,
        question: str,
        schema: str,
        user_id: int,
        model: str,
        error_context: str | None = None,
    ) -> dict[str, Any]:
        repair = (
            f"\n\nOprav predchádzajúci pokus podľa tejto chyby:\n{error_context}"
            if error_context
            else ""
        )
        result = self.reply(
            messages=[{"role": "user", "content": question}],
            user_id=user_id,
            model=model,
            system_prompt=(
                "Si SQL planner pre syntetickú SQLite analytickú databázu. "
                "Vráť iba jeden vykonateľný read-only SELECT alebo WITH dotaz, "
                "bez markdownu a bez komentára. Používaj iba uvedené tabuľky a "
                "stĺpce. Pre tržby použi quantity * unit_price; unit_price už "
                "obsahuje zľavu. Ak používateľ neurčí obdobie, použi všetky dáta. "
                "Nikdy nepouži PRAGMA, DDL, DML, attach ani viac statementov.\n\n"
                f"SCHEMA:\n{schema}{repair}"
            ),
        )
        sql = self._extract_sql(result["text"])
        return {
            "sql": sql,
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
        }

    def create_sql_report(
        self,
        *,
        question: str,
        sql: str,
        query_result: dict[str, Any],
        user_id: int,
        model: str,
    ) -> dict[str, Any]:
        payload = json.dumps(query_result, ensure_ascii=False, default=str)
        return self.reply(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Požiadavka:\n{question}\n\nSQL:\n{sql}\n\n"
                        f"Výsledok dotazu:\n{payload}"
                    ),
                }
            ],
            user_id=user_id,
            model=model,
            system_prompt=(
                "Vytvor hotový manažérsky report z výsledku SQL nad úplne "
                "fiktívnymi dátami. Odpovedaj v jazyku používateľa. Začni "
                "výrazným názvom REPORT / …, potom uveď stručné zhrnutie, "
                "kľúčové zistenia s konkrétnymi hodnotami, prípadne kompaktnú "
                "textovú tabuľku a záver. Jasne označ, že dáta sú syntetické. "
                "Nevymýšľaj hodnoty mimo výsledku. Ak je výsledok prázdny, "
                "vysvetli to ako platný výsledok. Na konci pridaj sekciu "
                "METODIKA s vykonaným SQL a počtom vrátených riadkov."
            ),
        )

    @staticmethod
    def _extract_sql(text: str) -> str:
        candidate = text.strip()
        fenced = re.fullmatch(
            r"```(?:sql)?\s*(.*?)\s*```", candidate, re.IGNORECASE | re.DOTALL
        )
        if fenced:
            candidate = fenced.group(1).strip()
        try:
            value = json.loads(candidate)
            if isinstance(value, dict) and isinstance(value.get("sql"), str):
                candidate = value["sql"].strip()
        except json.JSONDecodeError:
            pass
        return candidate

    def _responses_reply(
        self,
        *,
        messages: list[dict[str, str]],
        user_id: int,
        model: str,
        system_prompt: str,
    ) -> dict[str, Any]:
        client = OpenAI(api_key=self.api_key, timeout=90.0, max_retries=2)
        response = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=[
                {"role": message["role"], "content": message["content"]}
                for message in messages[-24:]
            ],
            reasoning={"effort": "low"},
            text={"verbosity": "medium"},
            max_output_tokens=1800,
            store=False,
            safety_identifier=hashlib.sha256(
                f"nexus-user-{user_id}".encode("utf-8")
            ).hexdigest()[:32],
        )
        usage = getattr(response, "usage", None)
        return {
            "text": response.output_text.strip(),
            "model": model,
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        }

    def _chat_completions_reply(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        system_prompt: str,
    ) -> dict[str, Any]:
        client_kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "timeout": 90.0,
            "max_retries": 2,
        }
        if "openrouter.ai" in self.base_url:
            client_kwargs["default_headers"] = {
                "HTTP-Referer": "https://raizenko.cloud/nexus/",
                "X-Title": "NexusChat",
            }
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                *[
                    {"role": message["role"], "content": message["content"]}
                    for message in messages[-24:]
                ],
            ],
            max_tokens=1800,
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        return {
            "text": text.strip(),
            "model": model,
            "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        }
