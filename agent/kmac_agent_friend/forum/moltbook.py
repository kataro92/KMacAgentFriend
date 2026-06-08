"""Moltbook forum client."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from kmac_agent_friend.forum.sanitizer import sanitize_forum_text


@dataclass
class ForumPost:
    id: str
    author: str
    title: str
    body: str


@dataclass
class ForumFeed:
    ok: bool
    posts: list[ForumPost]
    error: str = ""


class MoltbookClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def fetch_feed(self, *, timeout: float = 10.0) -> ForumFeed:
        if not self.base_url:
            return ForumFeed(ok=False, posts=[], error="MOLTBOOK_URL not configured")

        url = f"{self.base_url}/feed"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            return ForumFeed(ok=False, posts=[], error=str(exc))

        posts: list[ForumPost] = []
        for item in data.get("posts", []):
            posts.append(
                ForumPost(
                    id=str(item.get("id", "")),
                    author=sanitize_forum_text(str(item.get("author", "anonymous"))),
                    title=sanitize_forum_text(str(item.get("title", ""))),
                    body=sanitize_forum_text(str(item.get("body", ""))),
                )
            )
        return ForumFeed(ok=True, posts=posts)
