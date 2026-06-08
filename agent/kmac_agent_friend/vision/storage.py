"""Frame persistence policy for camera/vision captures.

By default the agent never writes captured frames to disk — they are analyzed
in memory and discarded. Persistence is opt-in via ``vision_persist_frames`` so
the user explicitly chooses to keep imagery around.
"""

from __future__ import annotations

import time
from pathlib import Path

from kmac_agent_friend.config import Settings

CAPTURES_DIRNAME = "captures"


def captures_dir(settings: Settings) -> Path:
    return settings.kaf_data_dir / CAPTURES_DIRNAME


def maybe_persist_frame(
    image_bytes: bytes,
    settings: Settings,
    *,
    suffix: str = ".jpg",
) -> Path | None:
    """Persist a frame only when the user has opted in; otherwise return ``None``."""
    if not settings.vision_persist_frames:
        return None
    if not image_bytes:
        return None
    target_dir = captures_dir(settings)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"capture-{int(time.time() * 1000)}{suffix}"
    path.write_bytes(image_bytes)
    return path
