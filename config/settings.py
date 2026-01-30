"""Application configuration using dotenv."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def _env_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Neo4j
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None
    neo4j_database: str | None = None

    # LLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    llm_enabled: bool = True
    llm_provider: str = "anthropic"
    llm_model: str | None = None
    llm_fallback_provider: str | None = None

    # Application
    log_level: str | None = "INFO"
    environment: str | None = "development"

    def __init__(self):
        # Load neo4j settings
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_username = os.getenv("NEO4J_USERNAME")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")
        self.neo4j_database = os.getenv("NEO4J_DATABASE")

        # Load LLM settings
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        self.llm_enabled = _env_bool(os.getenv("LLM_ENABLED"), True)
        self.llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
        self.llm_model = os.getenv("LLM_MODEL")
        self.llm_max_classify_tokens = int(os.getenv("LLM_MAX_CLASSIFY_TOKENS", "500"))
        self.llm_max_synthesize_tokens = int(os.getenv("LLM_MAX_SYNTHESIZE_TOKENS", "1000"))
        self.llm_fallback_provider = os.getenv("LLM_FALLBACK_PROVIDER")
        self.llm_fallback_max_classify_tokens = int(os.getenv("LLM_FALLBACK_MAX_CLASSIFY_TOKENS", "500"))
        self.llm_fallback_max_synthesize_tokens = int(os.getenv("LLM_FALLBACK_MAX_SYNTHESIZE_TOKENS", "2000"))

        # Raise error if required settings are missing
        required_fields = [
            "neo4j_uri",
            "neo4j_username",
            "neo4j_password",
            "neo4j_database",
        ]
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Missing required setting: {field}")

        print("Loaded settings:")
        print(f"  NEO4J_URI: {self.neo4j_uri}")
        print(f"  NEO4J_USERNAME: {self.neo4j_username}")
        print(f"  NEO4J_DATABASE: {self.neo4j_database}")
        print(f"  LLM_ENABLED: {self.llm_enabled}")
        print(f"  LLM_PROVIDER: {self.llm_provider}")
        print(f"  LLM_MODEL: {self.llm_model}")


_cached_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = Settings()
    return _cached_settings


def reset_settings() -> None:
    """Clear cached settings. Useful for testing or CLI overrides."""
    global _cached_settings
    _cached_settings = None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Print application settings.")
    parser.add_argument("--llm-provider", "-p", default="openai")
    parser.add_argument("--llm-model", "-m", default="gpt-4o-mini")
    args = parser.parse_args()
    settings = get_settings()
    settings.llm_provider = args.llm_provider
    settings.llm_model = args.llm_model
    print(settings)
