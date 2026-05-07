# -*- coding: utf-8 -*-
"""
FastAPI Web 后端
================

阶段 1：框架 + 静态前端 + SSE 实时日志通道

后续阶段会在此文件持续追加 API：
  - 阶段 2：注册（/api/register/*）
  - 阶段 3：代理（/api/proxies/*, /api/chain/*）
  - 阶段 4：账号管理（/api/augment/accounts/*）
  - 阶段 5：邮件监听 + 数据管理

启动：
    python -m web.server          # 直接跑，不重载
    python main.py                # 默认走这条
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import logger
from web.log_bus import get_bus, install_capture
from web.api.register import router as register_router
from web.api.proxies import router as proxies_router
from web.api.monitor import router as monitor_router
from web.api.data import router as data_router
from web.api.misc import router as misc_router


WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"


app = FastAPI(title="Outlook Register Web", version="1.0.0")

# 本地工具，前端在同源访问，CORS 留宽松便于以后内网用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 各模块路由
app.include_router(register_router)
app.include_router(proxies_router)
app.include_router(monitor_router)
app.include_router(data_router)
app.include_router(misc_router)


@app.on_event("startup")
async def _on_startup() -> None:
    install_capture()
    logger.info("✅ Web 后端启动完成 (FastAPI)")


# ============================== 静态前端 ==============================

# 一定要 mount 在 / 之前，让 / 走我们自定义的 index.html 路由
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "service": "outlook-register-web", "version": app.version}


# ============================== SSE 日志 ==============================

@app.get("/api/logs/stream")
async def logs_stream(request: Request) -> StreamingResponse:
    """
    SSE 实时日志通道。
    前端通过 EventSource('/api/logs/stream') 订阅。
    每 15 秒发一个心跳避免代理超时。
    """
    bus = get_bus()
    queue = bus.subscribe()
    loop = asyncio.get_event_loop()

    async def event_gen():
        try:
            # 欢迎消息
            hello = {
                "ts": "—",
                "level": "INFO",
                "msg": "🟢 已连接到日志通道",
            }
            yield f"data: {json.dumps(hello, ensure_ascii=False)}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                # 在 executor 中阻塞拿一条日志（threading.Queue.get 是阻塞的）
                try:
                    line = await loop.run_in_executor(None, queue.get, True, 15.0)
                    payload = json.dumps(line, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                except Exception:
                    # 15s 没日志 → 发心跳
                    yield ": ping\n\n"
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================== 启动入口 ==============================

def run(host: str = "127.0.0.1", port: int = 28942, reload: bool = False) -> None:
    """以编程方式启动 uvicorn"""
    import uvicorn
    uvicorn.run(
        "web.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run()
