from __future__ import annotations

from backend.llm.base import BackendInfo


class OllamaClient:
    def get_backend_info(self) -> BackendInfo:
        return BackendInfo(name="ollama", available=False)
