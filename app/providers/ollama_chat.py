from typing import Optional

import requests

from app.providers.ollama_embeddings import OllamaProviderError


class OllamaChatProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 60,
        session: Optional[requests.Session] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()

    def generate(self, prompt: str) -> str:
        payload = {"model": self._model, "prompt": prompt, "stream": False}
        url = f"{self._base_url}/api/generate"
        try:
            response = self._session.post(url, json=payload, timeout=self._timeout_seconds)
        except requests.RequestException as exc:
            raise OllamaProviderError(f"Failed to connect to Ollama chat API: {exc}") from exc

        if response.status_code >= 400:
            raise OllamaProviderError(
                f"Ollama chat request failed with status {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaProviderError("Ollama chat API returned invalid JSON") from exc

        answer = data.get("response")
        if not isinstance(answer, str):
            raise OllamaProviderError("Ollama chat API response missing 'response' text")

        return answer.strip()

