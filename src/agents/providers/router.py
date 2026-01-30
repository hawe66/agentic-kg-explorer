"""Provider router for user-optional LLM usage."""

import os
from typing import Optional
from openai import DefaultHttpxClient

from config.settings import get_settings

from .anthropic import AnthropicProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .base import LLMProvider


_PROVIDER_DEFAULTS = {
    "anthropic": "claude-3-5-sonnet-20241022",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
}


def get_provider() -> Optional[LLMProvider]:
    """Return a provider instance based on settings, or None if disabled."""
    settings = get_settings()
    if not settings.llm_enabled:
        return None

    provider = _build_provider(settings.llm_provider, settings)
    if provider is not None:
        provider.max_classify_tokens = settings.llm_max_classify_tokens
        provider.max_synthesize_tokens = settings.llm_max_synthesize_tokens
        return provider

    if settings.llm_fallback_provider:
        provider = _build_provider(settings.llm_fallback_provider, settings)
        if provider is not None:
            provider.max_classify_tokens = settings.llm_fallback_max_classify_tokens
            provider.max_synthesize_tokens = settings.llm_fallback_max_synthesize_tokens
            return provider

    return None


def _build_provider(provider_name: str, settings) -> Optional[LLMProvider]:
    if not provider_name:
        return None

    provider = provider_name.lower()
    model = settings.llm_model or _PROVIDER_DEFAULTS.get(provider)
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            return None
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=model,
            http_client=_build_http_client(),
        )

    if provider == "openai":
        if not settings.openai_api_key:
            return None
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=model,
            http_client=_build_http_client_openai(),
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            return None
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=model,
            http_options=_build_http_options_gemini(),
        )

    return None


def _build_http_client() -> Optional[object]:
    ssl_cert_file = os.getenv("SSL_CERT_FILE")
    if ssl_cert_file and os.path.exists(ssl_cert_file):
        import httpx

        return httpx.Client(verify=ssl_cert_file)
    return None

def _build_http_client_openai() -> Optional[object]:
    cafile = os.getenv("SSL_CERT_FILE")
    if cafile and os.path.isfile(cafile):
        return DefaultHttpxClient(verify=cafile)
    return DefaultHttpxClient()


def _build_http_options_gemini() -> Optional[object]:
    from google.genai import types

    cafile = os.getenv("SSL_CERT_FILE")
    if cafile and os.path.isfile(cafile):
        return types.HttpOptions(api_version="v1alpha", client_args={"verify": cafile})
    return None