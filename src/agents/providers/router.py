"""Provider router — YAML-driven, no per-provider code changes needed."""

import importlib
import os
from pathlib import Path
from typing import Any, Optional
import pprint

import yaml

from config.settings import get_settings
from .base import LLMProvider


# ---------------------------------------------------------------------------
# Registry (loaded once from config/providers.yaml)
# ---------------------------------------------------------------------------

_registry: dict | None = None


def _load_registry() -> dict:
    global _registry
    if _registry is not None:
        return _registry
    config_path = Path(__file__).resolve().parents[3] / "config" / "providers.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
    _registry = data.get("providers", {})
    return _registry


# ---------------------------------------------------------------------------
# Unified SSL / HTTP client builder
# ---------------------------------------------------------------------------

def _get_ssl_context() -> Any:
    """Create an SSL context with custom CA certificates if configured."""
    import ssl
    cafile = os.getenv("SSL_CERT_FILE")
    if cafile and os.path.isfile(cafile):
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cafile)
        return ctx
    return None


def _build_ssl_client(ssl_client_type: str | None) -> Any:
    """Build an SSL-aware HTTP client based on the provider's declared type."""
    if not ssl_client_type:
        return None

    ssl_ctx = _get_ssl_context()

    if ssl_client_type == "httpx":
        if ssl_ctx:
            import httpx
            return httpx.Client(verify=ssl_ctx)
        return None

    if ssl_client_type == "httpx_openai":
        from openai import DefaultHttpxClient
        if ssl_ctx:
            return DefaultHttpxClient(verify=ssl_ctx)
        return DefaultHttpxClient()

    if ssl_client_type == "gemini":
        from google.genai import types
        cafile = os.getenv("SSL_CERT_FILE")
        if cafile and os.path.isfile(cafile):
            return types.HttpOptions(
                api_version="v1alpha", client_args={"verify": cafile},
            )
        return None

    return None


# ---------------------------------------------------------------------------
# Public API (signature unchanged)
# ---------------------------------------------------------------------------

def get_provider() -> Optional[LLMProvider]:
    """Return a provider instance based on settings, or None if disabled."""
    settings = get_settings()
    if not settings.llm_enabled:
        print("[Provider Router] LLM disabled (LLM_ENABLED=false)")
        return None

    registry = _load_registry()
    primary_name = (settings.llm_provider or "").lower()
    primary_entry = registry.get(primary_name)
    print(f"[Provider Router] provider={primary_name!r}")
#    if primary_entry is None:
#        print("[Provider Router] provider not found in config/providers.yaml")
#    else:
#        print("[Provider Router] provider config:")
#        pprint.pprint(primary_entry)

    # --- primary provider ---
    provider = _build_provider(settings.llm_provider, settings, registry)
    if provider is not None:
        provider.max_classify_tokens = _resolve_int(
            settings, "llm_max_classify_tokens",
            primary_entry.get("max_classify_tokens") if primary_entry else None,
            500,
        )
        provider.max_synthesize_tokens = _resolve_int(
            settings, "llm_max_synthesize_tokens",
            primary_entry.get("max_synthesize_tokens") if primary_entry else None,
            1000,
        )
        return provider

    # --- fallback provider ---
    fallback_name = (
        os.getenv("LLM_FALLBACK_PROVIDER")
        or (primary_entry.get("fallback_provider") if primary_entry else None)
    )
    if fallback_name:
        print(f"[Provider Router] trying fallback provider={fallback_name!r}")
        fallback_entry = registry.get(fallback_name.lower())
        if fallback_entry is None:
            print("[Provider Router] fallback provider not found in config/providers.yaml")
        provider = _build_provider(fallback_name, settings, registry, is_fallback=True)
        if provider is not None:
            provider.max_classify_tokens = _resolve_int(
                settings, "llm_fallback_max_classify_tokens",
                fallback_entry.get("max_classify_tokens") if fallback_entry else None,
                500,
            )
            provider.max_synthesize_tokens = _resolve_int(
                settings, "llm_fallback_max_synthesize_tokens",
                fallback_entry.get("max_synthesize_tokens") if fallback_entry else None,
                2000,
            )
            return provider

    print("[Provider Router] no provider available (missing API key or bad config)")
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_provider(
    provider_name: str | None,
    settings,
    registry: dict,
    *,
    is_fallback: bool = False,
) -> Optional[LLMProvider]:
    if not provider_name:
        print("[Provider Router] no provider name set")
        return None

    name = provider_name.lower()
    entry = registry.get(name)
    if entry is None:
        print(f"[Provider Router] provider {name!r} not registered")
        return None

    # API key
    api_key = os.getenv(entry["api_key_env"], "")
    if not api_key:
        print(f"[Provider Router] missing API key env: {entry['api_key_env']}")
        return None

    # Model: .env override → fallback_model (if fallback) → YAML default_model
    if is_fallback:
        model = (
            os.getenv("LLM_FALLBACK_MODEL")
            or entry.get("default_model")
        )
    else:
        model = settings.llm_model or entry.get("default_model")
    if not model:
        print(f"[Provider Router] no model resolved for provider={name!r}")

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


def _resolve_int(
    settings, env_attr: str, yaml_default: int | None, hardcoded: int,
) -> int:
    """Resolve an int value: .env (via settings) → YAML default → hardcoded."""
    env_val = getattr(settings, env_attr, None)
    # settings.__init__ already reads from os.getenv with its own defaults,
    # so check whether the env var was explicitly set
    env_raw = os.getenv(env_attr.upper())
    if env_raw is not None:
        return int(env_raw)
    if yaml_default is not None:
        return int(yaml_default)
    return hardcoded
