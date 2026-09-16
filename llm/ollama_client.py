"""
Ollama LLM client wrapper for MentorOS.
Handles local LLM inference via Ollama's REST API (http://localhost:11434).
Supports automatic model detection, custom system prompts, and streaming responses.
"""

import json
from typing import Dict, Generator, List, Optional, Union
import urllib.error
import urllib.request


class OllamaClient:
    """HTTP client wrapper for Ollama local API."""

    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.model_name = model_name or self._auto_detect_model()

    def _auto_detect_model(self) -> str:
        """Fetch available models from Ollama and select best default model."""
        available = self.list_models()
        if not available:
            return "gemma4:e2b"  # fallback default

        # Prefer qwen2.5:7b-instruct-q4_K_M if available, else gemma4:e2b, else first available
        preferred_order = ["qwen2.5:7b-instruct-q4_K_M", "qwen2.5:7b", "gemma4:e2b"]
        for pref in preferred_order:
            if pref in available:
                return pref

        return available[0]

    def list_models(self) -> List[str]:
        """List model names currently downloaded in Ollama."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", []) if "name" in m]
                return models
        except Exception:
            return []

    def is_available(self) -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a text completion from Ollama.

        Args:
            prompt: User query / filled prompt template.
            system_prompt: Optional system prompt to ground behavior.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Max tokens to generate.

        Returns:
            Extracted text response from Ollama.
        """
        url = f"{self.base_url}/api/generate"

        payload: Dict[str, Union[str, bool, dict]] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens  # type: ignore

        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "").strip()
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. Is Ollama running? Error: {e}"
            ) from e

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Stream response chunks from Ollama as a generator."""
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                for line in response:
                    if line:
                        chunk_data = json.loads(line.decode("utf-8"))
                        text_chunk = chunk_data.get("response", "")
                        if text_chunk:
                            yield text_chunk
                        if chunk_data.get("done", False):
                            break
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Could not connect to Ollama streaming endpoint at {self.base_url}: {e}"
            ) from e
