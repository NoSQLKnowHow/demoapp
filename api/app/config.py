"""
Prism API configuration.
Loads settings from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Database
    oracle_dsn: str = os.environ.get("ORACLE_DSN", "")
    oracle_user: str = os.environ.get("ORACLE_USER", "prism")
    oracle_password: str = os.environ.get("ORACLE_PASSWORD", "")
    oracle_wallet_dir: str = os.environ.get("ORACLE_WALLET_DIR", "")

    # MongoDB API
    mongodb_uri: str = os.environ.get("MONGODB_URI", "")

    # Authentication
    auth_username: str = os.environ.get("PRISM_AUTH_USERNAME", "demo")
    auth_password: str = os.environ.get("PRISM_AUTH_PASSWORD", "")

    # Application
    mode: str = os.environ.get("PRISM_MODE", "local")
    allow_writes: bool = os.environ.get("PRISM_ALLOW_WRITES", "true").lower() == "true"

    # Connection pool
    pool_min: int = int(os.environ.get("PRISM_POOL_MIN", "2"))
    pool_max: int = int(os.environ.get("PRISM_POOL_MAX", "10"))
    pool_increment: int = int(os.environ.get("PRISM_POOL_INCREMENT", "1"))

    # Embedding model
    embedding_model: str = os.environ.get("PRISM_EMBEDDING_MODEL", "DEMO_MODEL")

    def validate(self):
        """Raise ValueError if required settings are missing."""
        missing = []
        if not self.oracle_dsn:
            missing.append("ORACLE_DSN")
        if not self.oracle_password:
            missing.append("ORACLE_PASSWORD")
        if not self.auth_password:
            missing.append("PRISM_AUTH_PASSWORD")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
