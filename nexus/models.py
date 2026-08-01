from __future__ import annotations

import os
import time
from typing import Any

import httpx


class OpenRouterModelCatalog:
    def __init__(self, base_url: str | None = None):
        configured = base_url if base_url is not None else os.getenv("OPENAI_BASE_URL", "")
        self.base_url = configured.rstrip("/")
        self._cached_at = 0.0
        self._cache: list[dict[str, Any]] = []

    def list_models(self) -> list[dict[str, Any]]:
        if self._cache and time.monotonic() - self._cached_at < 300:
            return self._cache
        if "openrouter.ai" not in self.base_url:
            return []
        response = httpx.get(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"},
            params={"output_modalities": "text", "sort": "most-popular"},
            timeout=15.0,
        )
        response.raise_for_status()
        models = []
        for item in response.json().get("data", []):
            pricing = item.get("pricing") or {}
            models.append(
                {
                    "id": str(item.get("id", "")),
                    "name": str(item.get("name") or item.get("id", "")),
                    "context_length": int(item.get("context_length") or 0),
                    "prompt_price": str(pricing.get("prompt") or "0"),
                    "completion_price": str(pricing.get("completion") or "0"),
                }
            )
        self._cache = [model for model in models if model["id"]]
        self._cached_at = time.monotonic()
        return self._cache
