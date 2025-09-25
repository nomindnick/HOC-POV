"""Ollama API client wrapper for local LLM integration"""
import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Model information from Ollama"""
    name: str
    model: str
    size: int
    digest: str
    modified_at: str
    details: Optional[Dict[str, Any]] = None

    @property
    def size_gb(self) -> float:
        """Return size in GB"""
        return self.size / (1024 ** 3)

    @property
    def size_display(self) -> str:
        """Return human-readable size"""
        gb = self.size_gb
        if gb >= 1:
            return f"{gb:.1f} GB"
        mb = self.size / (1024 ** 2)
        if mb >= 1:
            return f"{mb:.0f} MB"
        return f"{self.size} B"


class GenerateResponse(BaseModel):
    """Response from Ollama generate endpoint"""
    model: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class OllamaClient:
    """Async client for Ollama API"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0
    ):
        self.base_url = base_url
        self.timeout = timeout
        self._model_cache: Optional[List[ModelInfo]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)

    async def health_check(self) -> bool:
        """Check if Ollama is available and responding"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> List[ModelInfo]:
        """
        Get list of available models from Ollama
        Returns cached results if available and not expired
        """
        # Check cache
        if self._model_cache is not None and self._cache_timestamp is not None:
            if datetime.now() - self._cache_timestamp < self._cache_ttl:
                return self._model_cache

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()
                models = [
                    ModelInfo(**model_data)
                    for model_data in data.get("models", [])
                ]

                # Update cache
                self._model_cache = models
                self._cache_timestamp = datetime.now()

                return models

        except httpx.ConnectError:
            raise ConnectionError("Cannot connect to Ollama. Is it running?")
        except httpx.TimeoutException:
            raise TimeoutError("Ollama request timed out")
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error from Ollama: {e}")

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        format: Optional[str] = None,
        stream: bool = False
    ) -> GenerateResponse:
        """
        Generate text completion using specified model

        Args:
            prompt: Input prompt text
            model: Model name (e.g., "phi4-mini:3.8b")
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
            max_tokens: Maximum tokens to generate
            format: Response format ("json" for structured output)
            stream: Whether to stream response (not implemented)

        Returns:
            GenerateResponse with model output
        """
        if stream:
            raise NotImplementedError("Streaming not yet supported")

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
            "options": {}
        }

        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        if format == "json":
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()
                return GenerateResponse(**data)

        except httpx.ConnectError:
            raise ConnectionError("Cannot connect to Ollama. Is it running?")
        except httpx.TimeoutException:
            raise TimeoutError(f"Generation timed out after {self.timeout}s")
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error from Ollama: {e}")

    def clear_cache(self):
        """Clear the model cache"""
        self._model_cache = None
        self._cache_timestamp = None


# Global client instance
ollama_client = OllamaClient()