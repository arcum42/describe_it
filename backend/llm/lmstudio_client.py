from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from backend.llm.base import BackendInfo


class LMStudioClient:
    def __init__(self, base_url: str = "http://127.0.0.1:1234") -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str) -> dict:
        request = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                return json.loads(response.read().decode("utf-8"))
        except TimeoutError as error:
            raise ValueError(f"LM Studio request timed out at {self.base_url}.") from error
        except urllib.error.HTTPError as error:
            body = ""
            if error.fp is not None:
                body = error.fp.read().decode("utf-8", errors="replace")
            detail = body.strip() or error.reason
            raise ValueError(f"LM Studio request failed ({error.code}): {detail}") from error
        except urllib.error.URLError as error:
            raise ValueError(f"LM Studio is unreachable at {self.base_url}: {error.reason}") from error

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
            raise ValueError("LM Studio generation timed out. Try a smaller model or increase timeout.") from error
        except urllib.error.HTTPError as error:
            body = ""
            if error.fp is not None:
                body = error.fp.read().decode("utf-8", errors="replace")
            detail = body.strip() or error.reason
            raise ValueError(f"LM Studio request failed ({error.code}): {detail}") from error
        except urllib.error.URLError as error:
            raise ValueError(f"LM Studio is unreachable at {self.base_url}: {error.reason}") from error

    def list_models(self) -> list[str]:
        payload = self._get("/v1/models")
        data = payload.get("data") or []
        model_ids = [entry.get("id", "") for entry in data if isinstance(entry, dict)]
        return [model_id for model_id in model_ids if model_id]

    def get_backend_info(self) -> BackendInfo:
        try:
            models = self.list_models()
            return BackendInfo(name="lmstudio", available=True, models=models)
        except (TimeoutError, ValueError, json.JSONDecodeError) as error:
            return BackendInfo(name="lmstudio", available=False, models=[], error=str(error))

    def generate_caption(
        self,
        *,
        model: str,
        prompt: str,
        image_bytes: bytes | None = None,
        system_prompt: str = "",
        media_type: str = "image/png",
        timeout_seconds: int = 120,
    ) -> str:
        messages: list[dict[str, object]] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})

        content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        if image_bytes:
            image_b64 = base64.b64encode(image_bytes).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}})
        messages.append({"role": "user", "content": content})

        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }
        response = self._post("/v1/chat/completions", payload, timeout_seconds=timeout_seconds)
        choices = response.get("choices") or []
        if not choices:
            raise ValueError("LM Studio returned no choices.")
        message = choices[0].get("message") or {}
        text = (message.get("content") or "").strip()
        if not text:
            raise ValueError("LM Studio returned an empty caption response.")
        return text
