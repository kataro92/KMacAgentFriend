"""Application configuration."""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / "KMacAgentFriend"
DEFAULT_SANDBOX_DIR = DEFAULT_DATA_DIR / "sandbox"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    kaf_host: str = "127.0.0.1"
    kaf_port: int = 18750
    kaf_api_token: str = ""
    kaf_data_dir: Path = DEFAULT_DATA_DIR

    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"

    @property
    def sandbox_dir(self) -> Path:
        return self.kaf_data_dir / "sandbox"

    @property
    def bind_url(self) -> str:
        return f"http://{self.kaf_host}:{self.kaf_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_data_dirs(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    settings.kaf_data_dir.mkdir(parents=True, exist_ok=True)
    settings.sandbox_dir.mkdir(parents=True, exist_ok=True)


def resolve_api_token(settings: Settings) -> str:
    """Return configured token or generate and persist one."""
    if settings.kaf_api_token:
        return settings.kaf_api_token

    token_file = settings.kaf_data_dir / ".api_token"
    if token_file.is_file():
        return token_file.read_text(encoding="utf-8").strip()

    token = secrets.token_urlsafe(32)
    ensure_data_dirs(settings)
    token_file.write_text(token, encoding="utf-8")
    token_file.chmod(0o600)
    return token
