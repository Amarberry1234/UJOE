from __future__ import annotations

import logging
from typing import Iterable, List

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from .config import settings

logger = logging.getLogger(__name__)


class ModelClient:
    """Thin wrapper around an OpenAI-compatible chat/completions endpoint."""

    def __init__(self, endpoint: str | None = None, timeout: float = 30.0) -> None:
        self.endpoint = endpoint or settings.model_endpoint
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    def chat(self, messages: List[dict], max_tokens: int | None = None) -> str:
        url = f"{self.endpoint.rstrip('/')}/chat/completions"
        payload = {
            "model": "local-model",
            "messages": messages,
            "max_tokens": max_tokens or settings.model_max_tokens,
            "stream": False,
        }
        logger.debug("Sending chat payload to model", extra={"payload": payload})
        response = self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def embed(self, inputs: Iterable[str]) -> list[list[float]]:
        url = f"{self.endpoint.rstrip('/')}/embeddings"
        payload = {"input": list(inputs), "model": "embedding-model"}
        response = self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return [row["embedding"] for row in data.get("data", [])]
