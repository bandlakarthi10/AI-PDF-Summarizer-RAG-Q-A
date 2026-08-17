"""
Ollama LLM service.

- Checks connectivity and model availability before every generation call.
- Never fakes a response.
- Returns a clear RuntimeError when Ollama is unavailable.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging_config import logger


class LLMService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS

    # ── health / discovery ────────────────────────────────────

    async def check(self) -> Dict[str, Any]:
        """
        Returns a dict with keys:
            available: bool
            has_model: bool
            models: list[str]
            reason: str  (only when available=False)
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
            if r.status_code != 200:
                return {"available": False, "has_model": False, "models": [],
                        "reason": f"HTTP {r.status_code}"}
            models = [m["name"] for m in r.json().get("models", [])]
            has_model = any(self.model in m for m in models)
            return {"available": True, "has_model": has_model, "models": models}
        except Exception as exc:
            return {"available": False, "has_model": False, "models": [],
                    "reason": str(exc)}

    # ── generation ────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Send a generation request to Ollama.

        Raises:
            RuntimeError: Ollama not reachable.
            RuntimeError: Model not found (with pull instructions).
            TimeoutError: Generation exceeded timeout.
        """
        health = await self.check()
        if not health["available"]:
            raise RuntimeError(
                f"Ollama is not reachable at {self.base_url}. "
                f"Run `ollama serve` in a separate terminal. "
                f"Detail: {health.get('reason')}"
            )
        if not health["has_model"]:
            available = ", ".join(health["models"]) or "(none)"
            raise RuntimeError(
                f"Model '{self.model}' is not installed in Ollama. "
                f"Run `ollama pull {self.model}` to download it. "
                f"Currently installed: {available}"
            )

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        t0 = time.perf_counter()
        logger.info(f"Sending prompt to Ollama ({self.model}, T={temperature}) …")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Ollama did not respond within {self.timeout}s. "
                "Try a smaller document or a faster model."
            )

        if r.status_code == 404:
            raise RuntimeError(
                f"Model '{self.model}' returned 404. "
                f"Run `ollama pull {self.model}`."
            )
        if r.status_code != 200:
            raise RuntimeError(f"Ollama API error: HTTP {r.status_code} — {r.text}")

        answer = r.json().get("response", "").strip()
        elapsed = time.perf_counter() - t0
        logger.info(f"Ollama responded in {elapsed:.1f}s ({len(answer)} chars)")
        return answer


# ── singleton ─────────────────────────────────────────────────
llm_service = LLMService()
