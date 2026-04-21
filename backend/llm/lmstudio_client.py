from __future__ import annotations

from backend.llm.base import BackendInfo


class LMStudioClient:
    def get_backend_info(self) -> BackendInfo:
        return BackendInfo(name="lmstudio", available=False)
