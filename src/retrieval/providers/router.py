"""Embedding provider router — YAML-driven, matches LLM provider pattern."""

import importlib
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from .base import EmbeddingProvider


# ---------------------------------------------------------------------------
# Registry (loaded once from config/providers.yaml)
# ---------------------------------------------------------------------------

_registry: dict | None = None


def _load_registry() -> dict:
    """Load embedding providers from config/providers.yaml."""
    global _registry
    if _registry is not None:
        return _registry
    config_path = Path(__file__).resolve().parents[3] / "config" / "providers.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
    _registry = data.get("embedding_providers", {})
    return _registry


# ---------------------------------------------------------------------------
# SSL / HTTP client builder
# ---------------------------------------------------------------------------

def _build_ssl_client(ssl_client_type: str | None) -> Any:
    """Build an SSL-aware HTTP client based on provider's declared type."""
    if not ssl_client_type:
        return None

    cafile = os.getenv("SSL_CERT_FILE")

    if ssl_client_type == "httpx_openai":
        from openai import DefaultHttpxClient
        if cafile and os.path.isfile(cafile):
            return DefaultHttpxClient(verify=cafile)
        return DefaultHttpxClient()

    if ssl_client_type == "httpx":
        if cafile and os.path.isfile(cafile):
            import httpx
            return httpx.Client(verify=cafile)
        return None

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_embedding_provider() -> Optional[EmbeddingProvider]:
    """Return an embedding provider instance based on env vars.

    Provider selection:
        1. EMBEDDING_PROVIDER env var (default: 'openai')
        2. Fallback to EMBEDDING_FALLBACK_PROVIDER if primary fails

    Returns:
        EmbeddingProvider instance or None if unavailable.
    """
    registry = _load_registry()

    # Primary provider
    provider_name = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    provider = _build_provider(provider_name, registry)
    if provider is not None:
        print(f"[Embedding Router] provider={provider_name!r} model={provider.model!r}")
        return provider

    # Fallback
    primary_entry = registry.get(provider_name)
    fallback_name = (
        os.getenv("EMBEDDING_FALLBACK_PROVIDER")
        or (primary_entry.get("fallback_provider") if primary_entry else None)
    )
    if fallback_name:
        print(f"[Embedding Router] trying fallback provider={fallback_name!r}")
        provider = _build_provider(fallback_name.lower(), registry)
        if provider is not None:
            print(f"[Embedding Router] fallback provider={fallback_name!r} model={provider.model!r}")
            return provider

    print("[Embedding Router] no provider available (missing API key or bad config)")
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_provider(
    provider_name: str,
    registry: dict,
) -> Optional[EmbeddingProvider]:
    """Build an embedding provider instance from registry config."""
    entry = registry.get(provider_name)
    if entry is None:
        print(f"[Embedding Router] provider {provider_name!r} not in config/providers.yaml")
        return None

    # API key
    api_key = os.getenv(entry["api_key_env"], "")
    if not api_key:
        print(f"[Embedding Router] missing API key env: {entry['api_key_env']}")
        return None

    # Model: env override → YAML default
    model = os.getenv("EMBEDDING_MODEL") or entry.get("default_model")
    if not model:
        print(f"[Embedding Router] no model resolved for provider={provider_name!r}")
        return None

    # SSL
    ssl_obj = _build_ssl_client(entry.get("ssl_client_type"))

    # Dynamic import
    module = importlib.import_module(entry["module"])
    cls = getattr(module, entry["class"])

    # Constructor kwargs
    kwargs: dict[str, Any] = {"api_key": api_key, "model": model}
    ssl_kwarg = entry.get("constructor_ssl_kwarg")
    if ssl_kwarg and ssl_obj is not None:
        kwargs[ssl_kwarg] = ssl_obj

    return cls(**kwargs)
