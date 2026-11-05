"""
Backend application configuration.
Reads .env via python-dotenv from repo root.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DOTENV_PATH = REPO_ROOT / ".env"
load_dotenv(dotenv_path=DOTENV_PATH)


class Settings:
    """Application configuration settings loaded from environment."""

    def __init__(self) -> None:
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").strip().lower() in {
            "true",
            "1",
            "yes",
            "on",
        }
        self.DB_HOST: str = os.getenv("DB_HOST", "localhost")
        self.DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
        self.DB_USER: str = os.getenv("DB_USER", "cra_user")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "cra_password")
        self.DB_NAME: str = os.getenv("DB_NAME", "contract_risk_analyzer")

        self.JWT_SECRET: str = os.getenv("JWT_SECRET", "secret-key-change-in-production")
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

        self.UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
        self.MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))

        cors_str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        self.CORS_ORIGINS: List[str] = [
            origin.strip() for origin in cors_str.split(",") if origin.strip()
        ]


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application Settings."""
    return Settings()

