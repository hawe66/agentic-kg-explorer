"""Application configuration using dotenv."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Neo4j
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_llm: str = "anthropic"

    # Application
    log_level: str = "INFO"
    environment: str = "development"

    def __post_init__(self):
        # Load from environment with uppercase keys
        self.neo4j_uri = os.getenv("NEO4J_URI", self.neo4j_uri)
        self.neo4j_username = os.getenv("NEO4J_USERNAME", self.neo4j_username)
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", self.neo4j_password)
        self.neo4j_database = os.getenv("NEO4J_DATABASE", self.neo4j_database)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print(settings)
