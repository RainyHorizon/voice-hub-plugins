"""Standalone managed adapter; no audio.cpp imports or dependencies in Voice Hub."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import uvicorn

from server import UPSTREAM, app, local_url


def native_ready() -> bool:
    try:
        with httpx.Client(timeout=2, trust_env=False, follow_redirects=False) as client:
            response = client.get(UPSTREAM + "/health")
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return False
    try:
        response.raise_for_status()
        data = response.json()
        if (data.get("status") == "ok" and data.get("ui") is True
                and data.get("ui_management") is True and isinstance(data.get("backend"), str)):
            return True
    except (httpx.HTTPError, ValueError, AttributeError):
        pass
    raise ValueError("audio.cpp 端口已占用或原生 WebUI 管理功能未开启")


def native_command(directory: Path, backend: str) -> list[str]:
    name = "audiocpp_server.exe" if os.name == "nt" else "audiocpp_server"
    layouts = ["build/windows-cuda-release/bin", "build/windows-cpu-release/bin",
        "build/bin/Release", "build/bin", "bin", "."]
    if backend == "cpu":
        layouts[0], layouts[1] = layouts[1], layouts[0]
    executable = next((directory / layout / name for layout in layouts
                       if (directory / layout / name).is_file()), None)
    if executable is None:
        raise ValueError("未找到 audiocpp_server，请在插件齿轮中设置正确的 audio.cpp 安装目录")
    if backend == "auto":
        cache = executable.parent.parent / "CMakeCache.txt"
        cuda = cache.is_file() and "GGML_CUDA:BOOL=ON" in cache.read_text(errors="replace")
        cuda = cuda or any(executable.parent.glob("cublas64_*.dll"))
        backend = "cuda" if cuda else "cpu"
    address = urlsplit(UPSTREAM)
    return [str(executable.resolve()), "--ui", "--ui-management", "--backend", backend,
            "--host", address.hostname, "--port", str(address.port)]


def terminate(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--backend", choices=["auto", "cpu", "cuda", "vulkan", "metal"], default="auto")
    args = parser.parse_args()
    endpoint = urlsplit(local_url(args.endpoint))
    server = uvicorn.Server(uvicorn.Config(app, host=endpoint.hostname, port=endpoint.port, log_level="warning"))
    closed = threading.Event()
    native = None

    def parent_watch():
        os.read(sys.stdin.fileno(), 1)  # EOF on graceful shutdown or backend death.
        closed.set()
        server.should_exit = True

    threading.Thread(target=parent_watch, daemon=True).start()
    try:
        if not native_ready():
            directory = Path(args.audio_dir).expanduser().resolve()
            command = native_command(directory, args.backend)
            native = subprocess.Popen(command, cwd=directory, stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            deadline = time.monotonic() + 30
            while not native_ready():
                if closed.is_set():
                    return
                if native.poll() is not None or time.monotonic() > deadline:
                    raise ValueError("audio.cpp 未能就绪，请检查构建及硬件后端")
                closed.wait(0.2)
            # Set the model library only for the native instance we just started.
            models = directory / "models"
            if models.is_dir():
                with httpx.Client(timeout=5, trust_env=False) as client:
                    response = client.post(UPSTREAM + "/v1/ui/models-root", json={"path": str(models)})
                    response.raise_for_status()
        if not closed.is_set():
            server.run()
    finally:
        terminate(native)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"audio.cpp 插件启动失败: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
