import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kmac_agent_friend.config import Settings
from kmac_agent_friend.performance import InferenceGate, pin_models


@pytest.mark.asyncio
async def test_inference_gate_serializes():
    gate = InferenceGate()
    order: list[str] = []

    async def worker(label: str, delay: float):
        async with gate.slot(label):
            order.append(f"start:{label}")
            await asyncio.sleep(delay)
            order.append(f"end:{label}")

    await asyncio.gather(worker("a", 0.05), worker("b", 0.01))

    # No interleaving: each start is immediately followed by its own end.
    assert order in (
        ["start:a", "end:a", "start:b", "end:b"],
        ["start:b", "end:b", "start:a", "end:a"],
    )


@pytest.mark.asyncio
async def test_inference_gate_status_tracks_active():
    gate = InferenceGate()
    assert gate.status().active == ""
    async with gate.slot("chat"):
        assert gate.status().active == "chat"
    assert gate.status().active == ""


@pytest.mark.asyncio
async def test_pin_models_posts_keep_alive(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    with patch("kmac_agent_friend.performance.httpx.AsyncClient") as cls:
        cls.return_value.__aenter__.return_value = mock_client
        results = await pin_models(settings)

    assert results[settings.ollama_model] is True
    assert results[settings.ollama_embed_model] is True
    assert results[settings.ollama_vlm_model] is True
    # keep_alive must be present in at least one payload.
    payloads = [call.kwargs["json"] for call in mock_client.post.call_args_list]
    assert any("keep_alive" in p for p in payloads)
