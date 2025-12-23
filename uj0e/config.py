from __future__ import annotations

import os
from dataclasses import dataclass


def env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


@dataclass
class Settings:
    model_endpoint: str = env("MODEL_ENDPOINT", "http://localhost:8000/v1")
    model_max_tokens: int = int(env("MODEL_MAX_TOKENS", "512"))
    chroma_host: str = env("CHROMA_HOST", "localhost")
    chroma_port: int = int(env("CHROMA_PORT", "8000"))
    data_root: str = env("DATA_ROOT", os.path.abspath("data"))
    sandbox_memory: str = env("SANDBOX_MEMORY", "512m")
    sandbox_cpus: str = env("SANDBOX_CPUS", "0.5")
    sandbox_timeout: int = int(env("SANDBOX_TIMEOUT", "30"))
    audit_log: str = env("AUDIT_LOG", os.path.abspath("logs/audit.log"))

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


settings = Settings()
