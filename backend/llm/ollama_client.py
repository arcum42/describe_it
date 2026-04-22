from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from backend.llm.base import BackendInfo


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str) -> dict:
        request = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                return json.loads(response.read().decode("utf-8"))
        except TimeoutError as error:
            raise ValueError(f"Ollama request timed out at {self.base_url}.") from error
        except urllib.error.HTTPError as error:
            body = ""
            if error.fp is not None:
                body = error.fp.read().decode("utf-8", errors="replace")
            detail = body.strip() or error.reason
            raise ValueError(f"Ollama request failed ({error.code}): {detail}") from error
        except urllib.error.URLError as error:
            raise ValueError(f"Ollama is unreachable at {self.base_url}: {error.reason}") from error

    def _post(self, path: str, payload: dict, *, timeout_seconds: int = 120) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except TimeoutError as error:
            raise ValueError("Ollama generation timed out. Try a smaller model or increase timeout.") from error
        except urllib.error.HTTPError as error:
            body = ""
            if error.fp is not None:
                body = error.fp.read().decode("utf-8", errors="replace")
            detail = body.strip() or error.reason
            raise ValueError(f"Ollama request failed ({error.code}): {detail}") from error
        except urllib.error.URLError as error:
            raise ValueError(f"Ollama is unreachable at {self.base_url}: {error.reason}") from error

    def list_models(self) -> list[str]:
        payload = self._get("/api/tags")
        models = payload.get("models") or []
        names = [model.get("name", "") for model in models if isinstance(model, dict)]
        return [name for name in names if name]

    def get_backend_info(self) -> BackendInfo:
        try:
            models = self.list_models()
            return BackendInfo(name="ollama", available=True, models=models)
        except (TimeoutError, ValueError, json.JSONDecodeError) as error:
            return BackendInfo(name="ollama", available=False, models=[], error=str(error))

    def generate_caption(
        self,
        *,
        model: str,
        prompt: str,
        image_bytes: bytes | None = None,
        system_prompt: str = "",
        timeout_seconds: int = 120,
    ) -> str:
        payload: dict[str, object] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt.strip():
            payload["system"] = system_prompt.strip()
        if image_bytes:
            payload["images"] = [base64.b64encode(image_bytes).decode("ascii")]
        response = self._post("/api/generate", payload, timeout_seconds=timeout_seconds)
        text = (response.get("response") or "").strip()
        if not text:
            raise ValueError("Ollama returned an empty caption response.")
        return text
