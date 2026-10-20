"""Bridge audio.cpp's offline TTS to Voice Hub; its native UI supplies all tasks."""
from __future__ import annotations

import asyncio
import hashlib
import io
import ipaddress
import json
import os
import re
import shutil
import tempfile
import wave
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware


def local_url(value: str) -> str:
    try:
        url = urlsplit(value.strip().rstrip("/"))
        if (url.scheme != "http" or not ipaddress.ip_address(url.hostname or "").is_loopback
                or not url.port or url.username or url.password or url.query or url.fragment):
            raise ValueError
    except ValueError:
        raise ValueError("audio.cpp 地址须为带端口的数字回环 HTTP 地址") from None
    return url.geturl()


UPSTREAM = local_url(os.getenv("AUDIOCPP_URL", "http://127.0.0.1:8080"))
MAX_AUDIO = 50 * 1024 * 1024
DEFAULT_VOICE = "server-default"
app = FastAPI(title="Voice Hub · audio.cpp", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "test"])
_speech_lock = asyncio.Lock()


@app.middleware("http")
async def local_service(request: Request, call_next):
    if request.headers.get("origin") or request.headers.get("sec-fetch-site") == "cross-site":
        return Response(status_code=403)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={"detail": "合成参数无效"})


async def upstream(route: str, *, payload: dict | None = None, limit: int = 2 * 1024 * 1024) -> bytes:
    try:
        async with httpx.AsyncClient(timeout=150 if payload is not None else 10, trust_env=False, follow_redirects=False) as client:
            async with client.stream("POST" if payload is not None else "GET", UPSTREAM + route, json=payload) as response:
                response.raise_for_status()
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > limit:
                        raise HTTPException(502, "audio.cpp 响应超过大小限制")
                return bytes(data)
    except httpx.TimeoutException:
        raise HTTPException(504, "audio.cpp 请求超时，请在原生工作台检查模型状态或缩短文本") from None
    except httpx.HTTPError:
        raise HTTPException(502, "无法调用 audio.cpp，请检查服务、模型与参考音色配置") from None


async def upstream_json(route: str) -> dict:
    try:
        data = json.loads(await upstream(route))
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (ValueError, TypeError):
        raise HTTPException(502, "audio.cpp 返回了无效目录") from None


def public_id(value: str, limit: int, prefix: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9._-]{1," + str(limit) + r"}", value) and value != DEFAULT_VOICE:
        return value
    return prefix + hashlib.sha256(value.encode()).hexdigest()[:40]


async def catalog() -> list[dict]:
    data = (await upstream_json("/v1/models")).get("data")
    if not isinstance(data, list):
        raise HTTPException(502, "audio.cpp 返回了无效模型目录")
    result = []
    for model in data:
        if not isinstance(model, dict) or model.get("task") not in {"tts", "clon"} or model.get("mode") != "offline":
            continue
        name = model.get("id")
        if not isinstance(name, str) or not name or len(name) > 1000:
            raise HTTPException(502, "audio.cpp 返回了无效模型 ID")
        result.append({"id": public_id(name, 64, "m-"), "native_id": name,
                       "name": name[:100], "languages": ["und"]})
    if len(result) > 100 or len({m["id"] for m in result}) != len(result):
        raise HTTPException(502, "audio.cpp 模型目录超过限制或 ID 冲突")
    return result


async def model_voices(model: dict) -> dict[str, str | None]:
    query = str(httpx.QueryParams({"model": model["native_id"]}))
    names = (await upstream_json("/v1/audio/voices?" + query)).get("voices")
    if not isinstance(names, list) or any(not isinstance(v, str) or not v or len(v) > 1000 for v in names):
        raise HTTPException(502, "audio.cpp 返回了无效音色目录")
    result = {DEFAULT_VOICE: None}
    for name in names:
        result[public_id(name, 100, "v-")] = name
    return result


@app.get("/health")
async def health():
    data = await upstream_json("/health")
    if data.get("status") != "ok":
        raise HTTPException(503, "audio.cpp 尚未就绪")
    return {"id": "audio-cpp", "api_version": "1", "version": "0.2.0", "upstream": UPSTREAM}


@app.get("/models")
async def models():
    return {"models": [{k: v for k, v in m.items() if k != "native_id"} for m in await catalog()]}


@app.get("/voices")
async def voices():
    result = []
    for model in await catalog():
        for voice_id, name in (await model_voices(model)).items():
            result.append({"id": voice_id, "name": name[:100] if name else "服务默认音色",
                           "model": model["id"], "languages": ["und"]})
            if len(result) > 5000:
                raise HTTPException(502, "audio.cpp 音色目录超过限制")
    return {"voices": result}


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Speech(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(max_length=64)
    voice: str = Field(max_length=100)
    text: str = Field(min_length=1, max_length=10000)
    speed: float = Field(default=1, ge=0.25, le=4, allow_inf_nan=False)
    config: Preferences = Field(default_factory=Preferences)


def validate_wav(data: bytes) -> None:
    try:
        with wave.open(io.BytesIO(data), "rb") as audio:
            frames, channels, rate = audio.getnframes(), audio.getnchannels(), audio.getframerate()
            if (frames <= 0 or rate <= 0 or channels not in {1, 2} or audio.getsampwidth() != 2
                    or len(audio.readframes(frames)) != frames * channels * 2):
                raise ValueError
    except (wave.Error, EOFError, ValueError):
        raise HTTPException(502, "audio.cpp 未返回完整的 16-bit PCM WAV 音频") from None


async def change_speed(data: bytes, speed: float) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(503, "调整语速需要 FFmpeg，请安装并加入 PATH")
    # Use two factors to support FFmpeg builds whose atempo range is 0.5–2.
    factor = speed ** 0.5
    with tempfile.TemporaryDirectory(prefix="voice-hub-audiocpp-") as directory:
        source, output = Path(directory) / "input.wav", Path(directory) / "output.wav"
        await asyncio.to_thread(source.write_bytes, data)
        process = await asyncio.create_subprocess_exec(
            ffmpeg, "-nostdin", "-v", "error", "-i", str(source), "-af", f"atempo={factor},atempo={factor}",
            "-c:a", "pcm_s16le", "-fs", str(MAX_AUDIO + 1), str(output),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(process.wait(), 20)
            if process.returncode or not output.is_file() or output.stat().st_size > MAX_AUDIO:
                raise HTTPException(502, "语速调整失败或输出音频过大")
            return await asyncio.to_thread(output.read_bytes)
        except asyncio.TimeoutError:
            raise HTTPException(504, "语速调整超时") from None
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()


@app.post("/speech")
async def speech(body: Speech):
    if _speech_lock.locked():
        raise HTTPException(409, "插件正在合成，请等待当前任务完成")
    async with _speech_lock:
        selected = next((m for m in await catalog() if m["id"] == body.model), None)
        if selected is None:
            raise HTTPException(400, "模型不可用，请在 audio.cpp 注册离线语音模型后同步插件")
        choices = await model_voices(selected)
        if body.voice not in choices:
            raise HTTPException(400, "音色不可用，请同步插件音色目录")
        payload = {"model": selected["native_id"], "input": body.text, "response_format": "wav"}
        if choices[body.voice] is not None:
            payload["voice"] = choices[body.voice]
        data = await upstream("/v1/audio/speech", payload=payload, limit=MAX_AUDIO)
        await asyncio.to_thread(validate_wav, data)
        if body.speed != 1:
            data = await change_speed(data, body.speed)
            await asyncio.to_thread(validate_wav, data)
        return Response(data, media_type="audio/wav")
