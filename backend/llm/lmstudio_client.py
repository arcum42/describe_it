from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from backend.llm.base import BackendInfo, ModelInfo


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

    def _extract_model_entries(self, payload: object) -> list[dict[str, object]]:
        if isinstance(payload, list):
            return [entry for entry in payload if isinstance(entry, dict)]
        if not isinstance(payload, dict):
            return []

        for key in ("data", "models"):
            items = payload.get(key)
            if isinstance(items, list):
                return [entry for entry in items if isinstance(entry, dict)]
        return []

    def _extract_capabilities(self, entry: dict[str, object]) -> list[str]:
        raw_capabilities = entry.get("capabilities")
        capabilities: list[str] = []

        if isinstance(raw_capabilities, list):
            for capability in raw_capabilities:
                if isinstance(capability, str):
                    value = capability.strip().lower()
                    if value:
                        capabilities.append(value)
            return capabilities

        if isinstance(raw_capabilities, dict):
            for key, value in raw_capabilities.items():
                if isinstance(value, bool) and value:
                    normalized = key.strip().lower()
                    if normalized:
                        capabilities.append(normalized)
            return capabilities

        return capabilities

    def _extract_modalities(self, entry: dict[str, object]) -> list[str]:
        modalities: list[str] = []
        for key in ("input_modalities", "modalities"):
            raw_modalities = entry.get(key)
            if not isinstance(raw_modalities, list):
                continue
            for modality in raw_modalities:
                if isinstance(modality, str):
                    value = modality.strip().lower()
                    if value:
                        modalities.append(value)
        return modalities

    def _model_name(self, entry: dict[str, object]) -> str:
        for key in ("key", "id", "name", "model"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _vision_capable(self, entry: dict[str, object], capabilities: list[str], modalities: list[str]) -> bool:
        raw_capabilities = entry.get("capabilities")
        if isinstance(raw_capabilities, dict):
            vision_value = raw_capabilities.get("vision")
            if isinstance(vision_value, bool):
                return vision_value

        return any(token in {"vision", "image", "image_input"} for token in capabilities) or "image" in modalities

    def _parse_models(self, entries: list[dict[str, object]]) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        for entry in entries:
            model_type = entry.get("type")
            if isinstance(model_type, str) and model_type.strip().lower() == "embedding":
                continue

            model_name = self._model_name(entry)
            if not model_name:
                continue

            capabilities = self._extract_capabilities(entry)
            modalities = self._extract_modalities(entry)
            vision_capable = self._vision_capable(entry, capabilities, modalities)

            models.append(
                ModelInfo(
                    name=model_name,
                    vision_capable=vision_capable,
                    capabilities=capabilities,
                )
            )
        return models

    def list_models(self) -> list[ModelInfo]:
        errors: list[str] = []
        for path in ("/api/v1/models", "/api/v0/models", "/v1/models"):
            try:
                payload = self._get(path)
                entries = self._extract_model_entries(payload)
                return self._parse_models(entries)
            except ValueError as error:
                errors.append(str(error))

        if errors:
            raise ValueError(errors[-1])
        return []

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
