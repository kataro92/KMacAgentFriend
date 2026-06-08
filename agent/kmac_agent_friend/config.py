"""Application configuration."""

from __future__ import annotations

import os
import secrets
import shutil
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from kmac_agent_friend.settings_store import load_user_overrides
from kmac_agent_friend.voice.stt import normalize_whisper_model

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DATA_DIR = Path.home() / "Library" / "Application Support" / "KMacAgentFriend"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_SANDBOX_DIR = DEFAULT_DATA_DIR / "sandbox"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kaf_host: str = "127.0.0.1"
    kaf_port: int = 18750
    kaf_api_token: str = ""
    kaf_data_dir: Path = DEFAULT_DATA_DIR

    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_vlm_model: str = "llava"
    ollama_embed_model: str = "nomic-embed-text"
    moltbook_url: str = ""
    whisper_model: str = "mlx-community/whisper-small-mlx"
    tts_language: str = "en"
    kaf_project_dirs: str = ""
    background_interval_seconds: float = 120.0
    hf_token: str = Field(default="", validation_alias="HF_TOKEN")

    # Phase 4 — vision: never write captured frames to disk unless explicitly enabled.
    vision_persist_frames: bool = False
    # Performance — keep Ollama models resident to avoid reload latency on 16 GB.
    pin_ollama_models: bool = True
    # Security — cap tool executions to throttle runaway loops.
    tool_rate_limit_per_minute: int = 60
    # Autopilot — when off, background autonomy stays read-only / suggestion-only.
    autopilot_enabled: bool = False
    # Mock mode — serve canned replies so the Swift UI works without Ollama.
    mock_mode: bool = False

    @field_validator("kaf_data_dir", mode="before")
    @classmethod
    def _default_data_dir(cls, value: object) -> object:
        if value is None:
            return DEFAULT_DATA_DIR
        if isinstance(value, str) and not value.strip():
            return DEFAULT_DATA_DIR
        return value

    @field_validator("kaf_api_token", mode="before")
    @classmethod
    def _empty_api_token(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return ""
        return value

    @property
    def sandbox_dir(self) -> Path:
        return self.kaf_data_dir / "sandbox"

    @property
    def bind_url(self) -> str:
        return f"http://{self.kaf_host}:{self.kaf_port}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    overrides = load_user_overrides(settings.kaf_data_dir)
    if overrides:
        settings = settings.model_copy(update=overrides)
    normalized_whisper = normalize_whisper_model(settings.whisper_model)
    if normalized_whisper != settings.whisper_model:
        settings = settings.model_copy(update={"whisper_model": normalized_whisper})
    _apply_runtime_env(settings)
    return settings


def _apply_runtime_env(settings: Settings) -> None:
    if settings.hf_token:
        os.environ["HF_TOKEN"] = settings.hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


def ensure_data_dirs(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    settings.kaf_data_dir.mkdir(parents=True, exist_ok=True)
    settings.sandbox_dir.mkdir(parents=True, exist_ok=True)


def migrate_legacy_data_dir(
    settings: Settings,
    *,
    legacy_dir: Path | None = None,
) -> bool:
    """Move runtime data from the old Library location into the project ``data/`` folder."""
    target = settings.kaf_data_dir.resolve()
    legacy = (legacy_dir or LEGACY_DATA_DIR).resolve()
    if target == legacy or not legacy.is_dir():
        return False

    if target.exists() and any(target.iterdir()):
        return False

    target.mkdir(parents=True, exist_ok=True)
    for item in legacy.iterdir():
        shutil.move(str(item), str(target / item.name))

    try:
        legacy.rmdir()
    except OSError:
        pass

    settings.sandbox_dir.mkdir(parents=True, exist_ok=True)
    return True


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
