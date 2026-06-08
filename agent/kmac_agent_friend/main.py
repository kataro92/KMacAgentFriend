"""FastAPI daemon entry point."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from fastapi import Depends, FastAPI, File, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kmac_agent_friend.activity_log import MAX_ENTRIES, activity_log
from kmac_agent_friend.agent import chat_with_tools
from kmac_agent_friend.auth import verify_token
from kmac_agent_friend.background import background_worker
from kmac_agent_friend.config import (
    ensure_data_dirs,
    get_settings,
    reload_settings,
    resolve_api_token,
)
from kmac_agent_friend.confirm import confirmation_manager
from kmac_agent_friend.forum import MoltbookClient as ForumClient
from kmac_agent_friend.memory import ConversationStore
from kmac_agent_friend.settings_store import (
    EDITABLE_FIELDS,
    UserSettingsPatch,
    migrate_stored_settings,
    patch_user_settings,
    user_settings_path,
)
from kmac_agent_friend.state import AgentStatus, agent_state
from kmac_agent_friend.tools import list_dir, read_file, run_shell, write_file
from kmac_agent_friend.vision import analyze_image
from kmac_agent_friend.voice import (
    chat_reply,
    model_status,
    resolve_whisper_model,
    speak_text,
    transcribe_for_turn,
    warm_whisper_model,
)
from kmac_agent_friend.voice.stt import (
    mlx_whisper_available,
    normalize_whisper_model,
    whisper_availability,
)
from kmac_agent_friend.ws_manager import ws_manager

logger = logging.getLogger(__name__)

_voice_download_tasks: dict[str, asyncio.Task[None]] = {}


async def _ollama_reachable(host: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{host.rstrip('/')}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


async def _record_activity(
    level: str,
    category: str,
    message: str,
    detail: dict[str, Any] | None = None,
    *,
    broadcast: bool = True,
) -> None:
    entry = activity_log.append(level, category, message, detail)
    if broadcast:
        await ws_manager.broadcast({"type": "activity", **entry.to_dict()})


async def _set_status(
    status: AgentStatus,
    *,
    action: str = "",
    broadcast: bool = True,
) -> None:
    agent_state.status = status
    agent_state.current_action = action
    detail: dict[str, Any] = {"status": status.value}
    if action:
        detail["action"] = action
    await _record_activity("info", "agent", f"Agent status: {status.value}", detail)
    if broadcast:
        await ws_manager.broadcast(_state_event())


def _state_event() -> dict[str, Any]:
    return {"type": "state", **agent_state.to_dict()}


async def _broadcast_voice_progress(
    step: str,
    message: str,
    percent: int | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "voice_progress",
        "step": step,
        "message": message,
    }
    if percent is not None:
        payload["percent"] = percent
    await ws_manager.broadcast(payload)
    detail: dict[str, Any] = {"step": step}
    if percent is not None:
        detail["percent"] = percent
    await _record_activity("info", "voice", message, detail)


async def _warm_voice_stt() -> None:
    settings = get_settings()
    if not mlx_whisper_available():
        await _record_activity("info", "voice", "mlx-whisper not installed", broadcast=True)
        return
    configured = settings.whisper_model
    model, fallback_note = resolve_whisper_model(configured)
    if fallback_note:
        await _record_activity("warn", "voice", fallback_note, {"configured": configured})
        await _broadcast_voice_progress("fallback", fallback_note)
    await _broadcast_voice_progress("warmup", f"Warming Whisper ({model})")
    result = await warm_whisper_model(model)
    if result.ok:
        await _record_activity("info", "voice", "Whisper model ready", {"model": model})
        await _broadcast_voice_progress("warmup", f"Whisper ready ({model})", 100)
    else:
        await _record_activity(
            "error",
            "voice",
            "Whisper model failed to load",
            {"model": model, "error": result.error},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    bootstrap = get_settings()
    if migrate_stored_settings(bootstrap.kaf_data_dir):
        reload_settings()
    settings = get_settings()
    ensure_data_dirs(settings)
    token = resolve_api_token(settings)
    logger.info("KMacAgentFriend daemon starting on %s", settings.bind_url)
    logger.info("Whisper model: %s", settings.whisper_model)
    if settings.hf_token:
        logger.info("Hugging Face token loaded from .env")
    else:
        logger.warning("No HF_TOKEN — public model downloads may be rate-limited")
    if not settings.kaf_api_token:
        logger.info("API token (save to .env as KAF_API_TOKEN): %s", token)
    warmup_task = asyncio.create_task(_warm_voice_stt())
    yield
    warmup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await warmup_task
    await background_worker.stop()
    logger.info("KMacAgentFriend daemon stopped")


app = FastAPI(title="KMacAgentFriend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # localhost only — Swift app uses token auth
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_http_activity(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if (
        request.method in {"POST", "PATCH", "PUT", "DELETE"}
        and path.startswith("/api/")
        and not path.startswith("/api/activity")
    ):
        await _record_activity(
            "debug",
            "http",
            f"{request.method} {path}",
            {"status_code": response.status_code},
        )
    return response


@app.get("/health")
async def health(_: str = Depends(verify_token)):
    settings = get_settings()
    ollama_ok = await _ollama_reachable(settings.ollama_host)
    return {
        "ok": True,
        "service": "kmac-agent-friend",
        "version": "0.1.0",
        "api_version": 4,
        "ollama": ollama_ok,
        "ollama_host": settings.ollama_host,
        "model": settings.ollama_model,
        "agent": agent_state.to_dict(),
    }


def _public_settings() -> dict[str, Any]:
    settings = get_settings()
    return {field: getattr(settings, field) for field in EDITABLE_FIELDS}


@app.get("/api/settings")
async def get_app_settings(_: str = Depends(verify_token)):
    settings = get_settings()
    return {
        "ok": True,
        "settings": _public_settings(),
        "paths": {
            "user_settings": str(user_settings_path(settings.kaf_data_dir)),
            "data_dir": str(settings.kaf_data_dir),
        },
        "daemon": {"host": settings.kaf_host, "port": settings.kaf_port},
    }


@app.patch("/api/settings")
async def update_app_settings(body: UserSettingsPatch, _: str = Depends(verify_token)):
    settings = get_settings()
    patch_user_settings(settings.kaf_data_dir, body)
    reload_settings()
    return {"ok": True, "settings": _public_settings()}


@app.get("/api/activity")
async def get_activity(limit: int = 200, _: str = Depends(verify_token)):
    return {"ok": True, "entries": activity_log.recent(limit=min(limit, MAX_ENTRIES))}


@app.post("/api/activity/clear")
async def clear_activity(_: str = Depends(verify_token)):
    activity_log.clear()
    await _record_activity("info", "system", "Activity log cleared", broadcast=True)
    return {"ok": True}


@app.get("/api/ollama/models")
async def list_ollama_models(_: str = Depends(verify_token)):
    settings = get_settings()
    host = settings.ollama_host.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{host}/api/tags")
        if response.status_code != 200:
            return {
                "ok": False,
                "reachable": False,
                "models": [],
                "error": f"HTTP {response.status_code}",
            }
        payload = response.json()
        models = sorted(
            {
                item.get("name", "")
                for item in payload.get("models", [])
                if isinstance(item, dict) and item.get("name")
            }
        )
        return {"ok": True, "reachable": True, "models": models}
    except httpx.HTTPError as exc:
        return {"ok": False, "reachable": False, "models": [], "error": str(exc)}


@app.get("/api/state")
async def get_state(_: str = Depends(verify_token)):
    return agent_state.to_dict()


@app.post("/api/ping")
async def ping(_: str = Depends(verify_token)):
    """Round-trip latency check for Swift shell."""
    return {"pong": True, "ts": time.time()}


class BackgroundStartRequest(BaseModel):
    task: str = "moltbook"
    interval_seconds: float = 30.0


@app.get("/api/background/status")
async def background_status(_: str = Depends(verify_token)):
    return {"ok": True, **background_worker.status(), "agent": agent_state.to_dict()}


@app.post("/api/background/start")
async def background_start(body: BackgroundStartRequest, _: str = Depends(verify_token)):
    await background_worker.start(body.task, interval=body.interval_seconds)
    agent_state.background_task = body.task
    await _set_status(AgentStatus.BACKGROUND, action=body.task)
    return {"ok": True, "task": body.task}


@app.post("/api/background/stop")
async def background_stop(_: str = Depends(verify_token)):
    await background_worker.stop()
    agent_state.background_task = ""
    await _set_status(AgentStatus.IDLE)
    return {"ok": True}


class WriteFileRequest(BaseModel):
    path: str
    content: str
    confirm: bool = False


@app.get("/api/tools/list")
async def tools_list(path: str = ".", _: str = Depends(verify_token)):
    settings = get_settings()
    result = list_dir(path, settings)
    if not result.ok:
        return {"ok": False, "error": result.error}
    return {"ok": True, "path": result.path, "entries": result.entries}


@app.get("/api/tools/read")
async def tools_read(path: str, _: str = Depends(verify_token)):
    settings = get_settings()
    result = read_file(path, settings)
    if not result.ok:
        return {"ok": False, "error": result.error}
    return {"ok": True, "path": result.path, "content": result.content}


@app.post("/api/tools/write")
async def tools_write(body: WriteFileRequest, _: str = Depends(verify_token)):
    settings = get_settings()
    result = write_file(body.path, body.content, settings, confirm=body.confirm)
    if not result.ok:
        payload: dict[str, Any] = {"ok": False, "error": result.error, "path": result.path}
        if result.needs_confirmation:
            payload["needs_confirmation"] = True
            await ws_manager.broadcast(
                {
                    "type": "confirm_request",
                    "action": "write_file",
                    "path": result.path,
                    "message": result.error,
                }
            )
        return payload
    return {"ok": True, "path": result.path}


class RunShellRequest(BaseModel):
    command: str
    cwd: str = "."
    confirm: bool = False


class InjectTextRequest(BaseModel):
    text: str


@app.post("/api/tools/run")
async def tools_run(body: RunShellRequest, _: str = Depends(verify_token)):
    settings = get_settings()
    await _set_status(AgentStatus.ACTING, action="shell")
    try:
        result = await run_shell(
            body.command,
            settings,
            cwd=body.cwd,
            confirm=body.confirm,
        )
        if not result.ok:
            payload: dict[str, Any] = {
                "ok": False,
                "error": result.error,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
            if result.needs_confirmation:
                payload["needs_confirmation"] = True
                await ws_manager.broadcast(
                    {
                        "type": "confirm_request",
                        "action": "run_shell",
                        "command": body.command,
                        "message": result.error,
                    }
                )
            return payload
        return {
            "ok": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    finally:
        await _set_status(AgentStatus.IDLE)


@app.post("/api/tools/inject")
async def tools_inject(body: InjectTextRequest, _: str = Depends(verify_token)):
    text = body.text.strip()
    if not text:
        return {"ok": False, "error": "Empty text"}
    await ws_manager.broadcast({"type": "inject_text", "text": text})
    return {"ok": True}


@app.post("/api/vision/analyze")
async def vision_analyze(
    file: UploadFile = File(...),
    prompt: str = "Describe what you see.",
    confirmed: bool = False,
    _: str = Depends(verify_token),
):
    if not confirmed:
        await ws_manager.broadcast(
            {
                "type": "confirm_request",
                "action": "camera_capture",
                "message": "Allow camera capture for vision analysis?",
                "detail": prompt,
            }
        )
        return {
            "ok": False,
            "needs_confirmation": True,
            "error": "Camera capture requires confirmed=true",
        }

    image_bytes = await file.read()
    if not image_bytes:
        return {"ok": False, "error": "Empty image file"}

    settings = get_settings()
    await _set_status(AgentStatus.ACTING, action="vision")
    try:
        result = await analyze_image(
            image_bytes,
            prompt,
            ollama_host=settings.ollama_host,
            model=settings.ollama_vlm_model,
        )
        if not result.ok:
            await _set_status(AgentStatus.ERROR, action=result.error)
            return {"ok": False, "error": result.error}
        await ws_manager.broadcast({"type": "reply", "text": result.description})
        return {"ok": True, "description": result.description}
    finally:
        await _set_status(AgentStatus.IDLE)


@app.get("/api/forum/feed")
async def forum_feed(_: str = Depends(verify_token)):
    settings = get_settings()
    client = ForumClient(settings.moltbook_url)
    feed = await client.fetch_feed()
    if not feed.ok:
        return {"ok": False, "error": feed.error, "posts": []}
    return {
        "ok": True,
        "posts": [
            {"id": p.id, "author": p.author, "title": p.title, "body": p.body}
            for p in feed.posts
        ],
    }


class ChatRequest(BaseModel):
    message: str
    use_tools: bool = False


@app.get("/api/conversations")
async def list_conversations(_: str = Depends(verify_token)):
    settings = get_settings()
    store = ConversationStore.from_settings(settings)
    return {"ok": True, "conversations": store.list_conversations()}


@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    _: str = Depends(verify_token),
):
    settings = get_settings()
    store = ConversationStore.from_settings(settings)
    return {
        "ok": True,
        "conversation_id": conversation_id,
        "messages": store.get_messages(conversation_id, limit=limit),
    }


@app.post("/api/chat")
async def chat(body: ChatRequest, _: str = Depends(verify_token)):
    settings = get_settings()
    text = body.message.strip()
    if not text:
        return {"ok": False, "error": "Empty message"}

    store = ConversationStore.from_settings(settings)

    await _set_status(AgentStatus.THINKING, action="chatting")
    try:
        if body.use_tools:
            result = await chat_with_tools(text, settings=settings, store=store)
        else:
            history = store.recent(limit=20)
            result = await chat_reply(
                text,
                ollama_host=settings.ollama_host,
                model=settings.ollama_model,
                history=history,
            )
            if result.ok:
                store.append("user", text)
                store.append("assistant", result.reply)
        if not result.ok:
            await _set_status(AgentStatus.ERROR, action=result.error)
            return {"ok": False, "error": result.error}

        agent_state.message_count += 1
        await ws_manager.broadcast({"type": "reply", "text": result.reply})
        return {"ok": True, "reply": result.reply}
    finally:
        await _set_status(AgentStatus.IDLE)


class SpeakRequest(BaseModel):
    text: str
    language: str = "en"


class VoiceDownloadRequest(BaseModel):
    model: str = ""


def _voice_download_active(model: str) -> bool:
    key = normalize_whisper_model(model)
    task = _voice_download_tasks.get(key)
    return task is not None and not task.done()


async def _download_whisper_model(model: str) -> None:
    try:
        await _broadcast_voice_progress("download", f"Downloading {model}", 0)
        result = await warm_whisper_model(model)
        if result.ok:
            await _record_activity("info", "voice", "Whisper model downloaded", {"model": model})
            await _broadcast_voice_progress("download", f"Download complete ({model})", 100)
        else:
            await _record_activity(
                "error",
                "voice",
                "Whisper download failed",
                {"model": model, "error": result.error},
            )
            await _broadcast_voice_progress("error", result.error or "Download failed")
    finally:
        _voice_download_tasks.pop(model, None)


@app.get("/api/voice/status")
async def voice_status(model: str | None = None, _: str = Depends(verify_token)):
    settings = get_settings()
    target = normalize_whisper_model(model or settings.whisper_model)
    availability = whisper_availability(target)
    return {
        "ok": True,
        "mlx_whisper": mlx_whisper_available(),
        **availability,
        "download_in_progress": _voice_download_active(target),
        "fast_model": model_status(settings.whisper_model)["fast_model"],
        "saved_model": normalize_whisper_model(settings.whisper_model),
        # Legacy fields for older clients
        "model": target,
        "model_ready": availability["ready"],
        "needs_download": availability["needs_download"],
    }


@app.post("/api/voice/download")
async def voice_download(body: VoiceDownloadRequest, _: str = Depends(verify_token)):
    if not mlx_whisper_available():
        return {"ok": False, "error": "mlx-whisper not installed. Run: pip install -e '.[voice]'"}

    settings = get_settings()
    model = normalize_whisper_model(body.model or settings.whisper_model)
    availability = whisper_availability(model)
    if not availability["needs_download"] and availability["ready"]:
        return {"ok": True, "model": model, "state": "ready"}
    if _voice_download_active(model):
        return {"ok": True, "model": model, "state": "downloading"}

    task = asyncio.create_task(_download_whisper_model(model))
    _voice_download_tasks[model] = task
    await _record_activity("info", "voice", "Whisper download started", {"model": model})
    return {"ok": True, "model": model, "state": "started"}


@app.post("/api/voice/speak")
async def voice_speak(body: SpeakRequest, _: str = Depends(verify_token)):
    await _set_status(AgentStatus.SPEAKING, action="speaking")
    try:
        result = await speak_text(body.text, language=body.language)
        if not result.ok:
            await _set_status(AgentStatus.ERROR, action=result.error)
            return {"ok": False, "error": result.error}
        return {"ok": True, "voice": result.voice}
    finally:
        await _set_status(AgentStatus.IDLE)


@app.post("/api/voice/transcribe")
async def voice_transcribe(
    file: UploadFile = File(...),
    _: str = Depends(verify_token),
):
    wav_bytes = await file.read()
    if not wav_bytes:
        return {"ok": False, "error": "Empty audio file"}

    settings = get_settings()
    await _set_status(AgentStatus.THINKING, action="transcribing")
    try:
        stt, _, _ = await transcribe_for_turn(
            wav_bytes,
            settings.whisper_model,
            on_progress=_broadcast_voice_progress,
        )
        if not stt.ok:
            await _set_status(AgentStatus.ERROR, action=stt.error)
            return {"ok": False, "error": stt.error}
        return {
            "ok": True,
            "transcript": stt.text,
            "language": stt.language,
        }
    finally:
        await _set_status(AgentStatus.IDLE)


@app.post("/api/voice/turn")
async def voice_turn(
    file: UploadFile = File(...),
    speak: bool = True,
    _: str = Depends(verify_token),
):
    """Full PTT turn: transcribe → Ollama chat → optional TTS."""
    wav_bytes = await file.read()
    if not wav_bytes:
        return {"ok": False, "error": "Empty audio file"}

    settings = get_settings()

    try:
        await _set_status(AgentStatus.THINKING, action="transcribing")
        stt, model_used, fallback_note = await transcribe_for_turn(
            wav_bytes,
            settings.whisper_model,
            on_progress=_broadcast_voice_progress,
        )
        if not stt.ok:
            await _set_status(AgentStatus.ERROR, action=stt.error)
            return {"ok": False, "error": stt.error}
        if fallback_note:
            await _record_activity(
                "warn",
                "voice",
                fallback_note,
                {"configured": settings.whisper_model, "used": model_used},
            )

        await ws_manager.broadcast(
            {
                "type": "transcript",
                "text": stt.text,
                "language": stt.language,
            }
        )
        await _record_activity(
            "info",
            "voice",
            "Speech transcribed",
            {"text": stt.text, "language": stt.language},
        )

        store = ConversationStore.from_settings(settings)
        history = store.recent(limit=20)

        await _set_status(AgentStatus.THINKING, action="chatting")
        await _broadcast_voice_progress("chat", f"Asking Ollama ({settings.ollama_model})")
        chat = await chat_reply(
            stt.text,
            ollama_host=settings.ollama_host,
            model=settings.ollama_model,
            history=history,
        )
        if not chat.ok:
            await _set_status(AgentStatus.ERROR, action=chat.error)
            return {
                "ok": False,
                "transcript": stt.text,
                "language": stt.language,
                "error": chat.error,
            }

        store.append("user", stt.text)
        store.append("assistant", chat.reply)
        await ws_manager.broadcast({"type": "reply", "text": chat.reply})
        await _record_activity("info", "voice", "Assistant reply", {"text": chat.reply})

        spoken = False
        voice = ""
        if speak and chat.reply:
            await _set_status(AgentStatus.SPEAKING, action="speaking")
            await _broadcast_voice_progress("tts", "Speaking reply")
            tts = await speak_text(
                chat.reply,
                language=stt.language or settings.tts_language or "en",
            )
            spoken = tts.ok
            voice = tts.voice
            if not tts.ok:
                await _set_status(AgentStatus.ERROR, action=tts.error)
                return {
                    "ok": False,
                    "transcript": stt.text,
                    "language": stt.language,
                    "reply": chat.reply,
                    "spoken": False,
                    "error": tts.error,
                }

        agent_state.message_count += 1
        return {
            "ok": True,
            "transcript": stt.text,
            "language": stt.language,
            "reply": chat.reply,
            "spoken": spoken,
            "voice": voice,
        }
    finally:
        if agent_state.status != AgentStatus.IDLE:
            await _set_status(AgentStatus.IDLE)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    settings = get_settings()
    token = websocket.query_params.get("token")
    expected = resolve_api_token(settings)

    if token != expected:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()
    await ws_manager.connect(websocket)
    agent_state.connected_clients = ws_manager.count
    logger.info("WebSocket client connected (%d total)", agent_state.connected_clients)
    await _record_activity(
        "info",
        "ws",
        "WebSocket client connected",
        {"clients": agent_state.connected_clients},
    )

    try:
        await websocket.send_json(_state_event())

        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "code": "invalid_json", "message": "Expected JSON"}
                )
                continue

            msg_type = message.get("type")

            if msg_type == "ping":
                started = time.perf_counter()
                await websocket.send_json(
                    {
                        "type": "pong",
                        "ts": time.time(),
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    }
                )
            elif msg_type == "get_state":
                await websocket.send_json(_state_event())
            elif msg_type == "ptt_start":
                await _set_status(AgentStatus.LISTENING, action="push-to-talk")
            elif msg_type == "ptt_end":
                if agent_state.status == AgentStatus.LISTENING:
                    await _set_status(AgentStatus.IDLE)
            elif msg_type == "confirm_response":
                request_id = str(message.get("request_id", ""))
                approved = bool(message.get("approved"))
                if request_id:
                    confirmation_manager.resolve(request_id, approved)
                await websocket.send_json(
                    {
                        "type": "confirm_ack",
                        "request_id": request_id,
                        "approved": approved,
                    }
                )
            elif msg_type == "inject_result":
                logger.info(
                    "inject_result ok=%s detail=%s",
                    message.get("ok"),
                    message.get("detail", ""),
                )
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "unknown_type",
                        "message": f"Unsupported message type: {msg_type}",
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)
        agent_state.connected_clients = ws_manager.count
        logger.info("WebSocket client disconnected (%d remaining)", agent_state.connected_clients)
        await _record_activity(
            "info",
            "ws",
            "WebSocket client disconnected",
            {"clients": agent_state.connected_clients},
        )


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # mlx-whisper model downloads; HF_TOKEN is optional for local use.
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)


def run() -> None:
    _configure_logging()
    settings = get_settings()
    uvicorn.run(
        "kmac_agent_friend.main:app",
        host=settings.kaf_host,
        port=settings.kaf_port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run()
