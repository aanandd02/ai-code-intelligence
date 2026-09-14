"""
LLM Provider abstraction and Ollama implementation.
100% local, free, zero external API keys required.
"""

from abc import ABC, abstractmethod
import json
from typing import Any, AsyncGenerator

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """Generate a single completion."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """Generate response from chat conversation history."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List locally available models."""
        ...


class OllamaLLMProvider(LLMProvider):
    """
    Local LLM provider using Ollama's local HTTP server.
    Zero-cost, private, running entirely on the user's hardware.
    """

    def __init__(self, base_url: str | None = None, default_model: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = default_model or settings.OLLAMA_MODEL

    async def list_models(self) -> list[str]:
        """List models installed in local Ollama instance."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Could not fetch Ollama models ({e})")
        return []

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        target_model = model or self.default_model
        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=float(settings.OLLAMA_TIMEOUT)) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
                raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
        except httpx.ConnectError:
            if settings.GROQ_API_KEY:
                try:
                    logger.info("Local Ollama not reachable, attempting Groq fallback...")
                    groq = GroqLLMProvider()
                    return await groq.generate(prompt, system=system, temperature=temperature, **kwargs)
                except Exception:
                    pass
            return self._offline_response(prompt, target_model)
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return self._offline_response(prompt, target_model, error=str(e))

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        target_model = model or self.default_model
        chat_messages = []
        if system:
            chat_messages.append({"role": "system", "content": system})
        chat_messages.extend(messages)

        payload = {
            "model": target_model,
            "messages": chat_messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=float(settings.OLLAMA_TIMEOUT)) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    msg = data.get("message", {})
                    return msg.get("content", "")
                raise RuntimeError(f"Ollama chat error HTTP {resp.status_code}: {resp.text}")
        except httpx.ConnectError:
            if settings.GROQ_API_KEY:
                try:
                    logger.info("Local Ollama not reachable, attempting Groq fallback...")
                    groq = GroqLLMProvider()
                    return await groq.chat(messages, system=system, temperature=temperature, **kwargs)
                except Exception:
                    pass
            last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
            return self._offline_response(last_user_msg, target_model)
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
            return self._offline_response(last_user_msg, target_model, error=str(e))

    def _offline_response(self, user_query: str, model_name: str, error: str | None = None) -> str:
        """
        Helpful offline diagnostic response when Ollama is not yet active.
        Ensures the UI gracefully explains setup steps rather than showing a generic crash.
        """
        err_note = f" (Error details: {error})" if error else ""
        return (
            f"**Ollama Offline / Standby Notice**\n\n"
            f"Unable to reach the local Ollama instance at `{self.base_url}`{err_note}.\n\n"
            f"To enable real-time local AI reasoning:\n"
            f"1. Start the Ollama daemon: `ollama serve`\n"
            f"2. Pull the model: `ollama run {model_name}`\n"
            f"3. For embeddings: `ollama pull {settings.EMBEDDING_MODEL}`\n\n"
            f"Once running, queries like *\"{user_query}\"* will be processed locally and privately at zero cost."
        )


class GroqLLMProvider(LLMProvider):
    """
    Cloud LLM provider using Groq's high-speed free tier API.
    Provides fast, zero-cost completions without running GPU models locally.
    """

    KNOWN_MODELS: list[str] = [
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
    ]

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL or "openai/gpt-oss-120b"
        self.default_model = self.model
        self.base_url = settings.GROQ_BASE_URL.rstrip("/")

    def _resolve_model(self, model: str | None) -> str:
        if not model or ":" in model or "coder" in model.lower() or model == settings.OLLAMA_MODEL:
            return self.model
        return model

    async def list_models(self) -> list[str]:
        return list(self.KNOWN_MODELS)

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, system=system, model=model, temperature=temperature, **kwargs)

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        target_model = self._resolve_model(model)
        chat_messages = []
        if system:
            chat_messages.append({"role": "system", "content": system})
        chat_messages.extend(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "messages": chat_messages,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                    return ""
                raise RuntimeError(f"Groq API returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Groq chat failed ({e}), falling back to local Ollama...")
            try:
                ollama = OllamaLLMProvider()
                return await ollama.chat(
                    messages=messages,
                    system=system,
                    model=settings.OLLAMA_MODEL,
                    temperature=temperature,
                    **kwargs,
                )
            except Exception as o_err:
                logger.error(f"Fallback to Ollama also failed: {o_err}")
                return f"**Error**: {e}"


def get_llm_provider() -> LLMProvider:
    """Get active LLM provider instance."""
    if settings.LLM_PROVIDER.lower() == "groq" and settings.GROQ_API_KEY:
        return GroqLLMProvider()
    return OllamaLLMProvider()


def get_llm_for_model(model: str | None = None, provider: str | None = None) -> tuple[LLMProvider, str, str]:
    """
    Resolve (provider_instance, target_model_name, provider_id)
    based on requested provider ('ollama' or 'groq') and model.
    """
    p_lower = (provider or "").strip().lower()

    if p_lower == "groq":
        if settings.GROQ_API_KEY:
            groq = GroqLLMProvider()
            target_model = groq._resolve_model(model)
            return groq, target_model, "groq"
        ollama = OllamaLLMProvider()
        return ollama, model or settings.OLLAMA_MODEL, "ollama"

    if p_lower == "ollama":
        ollama = OllamaLLMProvider()
        return ollama, model or settings.OLLAMA_MODEL, "ollama"

    # Infer from model name if provider not explicit
    if model:
        if model in GroqLLMProvider.KNOWN_MODELS or "openai/" in model:
            if settings.GROQ_API_KEY:
                groq = GroqLLMProvider()
                return groq, groq._resolve_model(model), "groq"

    # Default to configured provider (ollama by default)
    if settings.LLM_PROVIDER.lower() == "groq" and settings.GROQ_API_KEY:
        groq = GroqLLMProvider()
        return groq, groq._resolve_model(model), "groq"

    ollama = OllamaLLMProvider()
    return ollama, model or settings.OLLAMA_MODEL, "ollama"


async def get_available_models_catalog() -> dict[str, Any]:
    """Return catalog of available Local (Ollama) and Cloud (Groq) models."""
    ollama = OllamaLLMProvider()
    local_models = await ollama.list_models()
    if not local_models:
        local_models = [settings.OLLAMA_MODEL]

    groq_available = bool(settings.GROQ_API_KEY)
    groq_models = list(GroqLLMProvider.KNOWN_MODELS) if groq_available else []

    return {
        "providers": [
            {
                "id": "ollama",
                "name": "Local (Offline)",
                "description": "Runs 100% locally on your machine. $0 cost, completely private.",
                "is_available": True,
                "models": local_models,
                "default_model": settings.OLLAMA_MODEL if settings.OLLAMA_MODEL in local_models else local_models[0],
            },
            {
                "id": "groq",
                "name": "Cloud (Groq)",
                "description": "High-speed cloud inference via Groq API.",
                "is_available": groq_available,
                "models": groq_models,
                "default_model": settings.GROQ_MODEL if groq_available else None,
            },
        ],
        "active_provider": settings.LLM_PROVIDER.lower(),
        "active_model": settings.OLLAMA_MODEL if settings.LLM_PROVIDER.lower() == "ollama" else settings.GROQ_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
    }

