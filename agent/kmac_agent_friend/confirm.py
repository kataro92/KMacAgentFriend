"""User confirmation requests (Swift sheet via WebSocket)."""

from __future__ import annotations

import asyncio
import secrets

from kmac_agent_friend.ws_manager import ws_manager


class ConfirmationManager:
    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def ask(
        self,
        title: str,
        detail: str,
        *,
        timeout: float = 120.0,
    ) -> bool:
        request_id = secrets.token_urlsafe(8)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._pending[request_id] = future

        await ws_manager.broadcast(
            {
                "type": "confirm_request",
                "request_id": request_id,
                "title": title,
                "detail": detail,
            }
        )

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            return False
        finally:
            self._pending.pop(request_id, None)

    def resolve(self, request_id: str, approved: bool) -> bool:
        future = self._pending.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(approved)
        return True


confirmation_manager = ConfirmationManager()
