"""User-editable settings persisted under the KAF data directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from kmac_agent_friend.voice.stt import normalize_whisper_model

USER_SETTINGS_FILE = "user_settings.json"

# Fields the control panel may read and write (secrets like API token excluded).
EDITABLE_FIELDS = (
    "ollama_host",
    "ollama_model",
    "ollama_vlm_model",
    "ollama_embed_model",
    "whisper_model",
    "tts_language",
    "kaf_project_dirs",
    "moltbook_url",
    "background_interval_seconds",
    "vision_persist_frames",
    "pin_ollama_models",
    "tool_rate_limit_per_minute",
    "autopilot_enabled",
    "mock_mode",
)


class UserSettingsPatch(BaseModel):
    ollama_host: str | None = None
    ollama_model: str | None = None
    ollama_vlm_model: str | None = None
    ollama_embed_model: str | None = None
    whisper_model: str | None = None
    tts_language: str | None = None
    kaf_project_dirs: str | None = None
    moltbook_url: str | None = None
    background_interval_seconds: float | None = Field(default=None, gt=0)
    vision_persist_frames: bool | None = None
    pin_ollama_models: bool | None = None
    tool_rate_limit_per_minute: int | None = Field(default=None, ge=0)
    autopilot_enabled: bool | None = None
    mock_mode: bool | None = None


def user_settings_path(data_dir: Path) -> Path:
    return data_dir / USER_SETTINGS_FILE


def load_user_overrides(data_dir: Path) -> dict[str, Any]:
    path = user_settings_path(data_dir)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    overrides = {key: raw[key] for key in EDITABLE_FIELDS if key in raw}
    if "whisper_model" in overrides and isinstance(overrides["whisper_model"], str):
        overrides["whisper_model"] = normalize_whisper_model(overrides["whisper_model"])
    return overrides


def save_user_overrides(data_dir: Path, values: dict[str, Any]) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = user_settings_path(data_dir)
    existing = load_user_overrides(data_dir)
    existing.update(values)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def patch_user_settings(data_dir: Path, patch: UserSettingsPatch) -> dict[str, Any]:
    updates = patch.model_dump(exclude_none=True)
    if "whisper_model" in updates and isinstance(updates["whisper_model"], str):
        updates["whisper_model"] = normalize_whisper_model(updates["whisper_model"])
    if updates:
        save_user_overrides(data_dir, updates)
    return load_user_overrides(data_dir)


def migrate_stored_settings(data_dir: Path) -> bool:
    """Persist fixed whisper model IDs so clients stop using invalid repo names."""
    path = user_settings_path(data_dir)
    if not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(raw, dict) or "whisper_model" not in raw:
        return False
    if not isinstance(raw["whisper_model"], str):
        return False
    fixed = normalize_whisper_model(raw["whisper_model"])
    if fixed == raw["whisper_model"]:
        return False
    raw["whisper_model"] = fixed
    path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return True
