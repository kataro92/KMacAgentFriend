"""Strip unsafe content from forum posts."""

from __future__ import annotations

import re

_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_forum_text(text: str, *, max_len: int = 4000) -> str:
    cleaned = _CONTROL_RE.sub("", text or "")
    cleaned = _SCRIPT_RE.sub("", cleaned)
    cleaned = _TAG_RE.sub("", cleaned)
    cleaned = cleaned.strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1] + "…"
    return cleaned
