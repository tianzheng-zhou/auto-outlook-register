# -*- coding: utf-8 -*-
"""
注册 API
========

复刻 PyQt RegisterTab 的注册流程，包含：
- 取代理（按池轮换）
- 读链式代理设置
- 创建带代理的 driver
- 跑 OutlookRegistration（接管 progress / confirm / confirm_success 回调）
- 流程结束等用户允许后关闭浏览器

并发控制：进程内一次只跑一个注册任务（State.register.thread）。
"""
from __future__ import annotations

import threading
import traceback
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import logger
from web.log_bus import get_bus
from web.state import get_state


router = APIRouter(prefix="/api/register", tags=["register"])


# ============================== 请求模型 ==============================

class ConfirmSuccessReq(BaseModel):
    success: bool


# ============================== 工作线程 ==============================

def _register_worker() -> None:
    """注册任务主线程；逻辑对齐 PyQt RegisterTab.RegisterWorker"""
    state_root = get_state()
    state = state_root.register
    bus = get_bus()

    # progress callback
    def on_progress(msg: str) -> None:
        bus.publish("info", str(msg))

    # confirm（用户操作完成验证码后解阻塞）
    def on_confirm(message: str) -> None:
        ev = threading.Event()
        with state_root.lock:
            state.confirm_event = ev
            state.confirm_message = str(message)
            state.status = "waiting_confirm"
        bus.publish("warning", f"⏸ 等待用户确认：{message}")
        ev.wait()
        with state_root.lock:
            state.confirm_event = None
            state.confirm_message = ""
            if state.status == "waiting_confirm":
                state.status = "running"

    # confirm_success（注册结束让用户确认 是/否成功）
    def on_confirm_success(message: str) -> bool:
        ev = threading.Event()
        with state_root.lock:
            state.confirm_success_event = ev
            state.confirm_success_message = str(message)
            state.confirm_success_result = False
            state.status = "waiting_confirm_success"
        bus.publish("warning", "⏸ 等待用户在控制台确认注册结果")
        ev.wait()
        with state_root.lock:
            result = state.confirm_success_result
            state.confirm_success_event = None
            state.confirm_success_message = ""
            if state.status == "waiting_confirm_success":
                state.status = "running"
        return result

    try:
        bus.publish("info", "=" * 60)
        bus.publish("info", "🚀 开始新的注册任务")
        bus.publish("info", "=" * 60)

        # ---- 1. 取代理 ----
        from core.proxy import get_proxy_manager, create_stealth_browser
        from config.proxy_chain_settings import load_chain_settings, DEFAULT_UPSTREAM_URL
        from config.settings import Settings

        proxy_manager = get_proxy_manager()
        proxy = proxy_manager.get_next_proxy()
        if proxy:
            bus.publish("info", f"✅ 获取代理: {proxy.to_chrome_proxy()}")
        else:
            bus.publish("warning", "⚠️ 未配置代理，使用本地 IP")

        # ---- 2. 链式代理设置 ----
        upstream_proxy = None
        if proxy:
            try:
                chain_settings = load_chain_settings()
                if chain_settings.get("enabled"):
                    up_url = chain_settings.get("upstream_url") or DEFAULT_UPSTREAM_URL
                    upstream_proxy = proxy_manager._parse_proxy_string(up_url)
                    bus.publish(
                        "info",
                        f"🔗 启用链式代理：上游 {upstream_proxy.host}:{upstream_proxy.port}",
                    )
            except Exception as e:
                bus.publish("warning", f"⚠️ 解析上游代理失败，将忽略: {e}")
                upstream_proxy = None

        # ---- 3. 创建带代理的 driver ----
        bus.publish("info", "🌐 正在创建浏览器（含指纹伪装）...")
        driver = create_stealth_browser(
            chrome_version=Settings.CHROME_VERSION,
            headless=False,
            proxy=proxy,
            upstream_proxy=upstream_proxy,
        )
        bus.publish("info", "✅ 浏览器创建成功")

        # ---- 4. 创建 OutlookRegistration ----
        from core.outlook.outlook_register import OutlookRegistration

        registrar = OutlookRegistration(
            progress_callback=on_progress,
            confirm_callback=on_confirm,
            confirm_success_callback=on_confirm_success,
            driver=driver,
        )
        with state_root.lock:
            state.registrar = registrar

        # ---- 5. 跑注册 ----
        result: bool = bool(registrar.register())

        # 记录最终账号信息
        with state_root.lock:
            state.user_info = dict(registrar.user_info or {})
            state.email = state.user_info.get("email")

        if result:
            bus.publish("success", "✅ 注册流程完成")
        else:
            bus.publish("error", "❌ 注册失败")

        # ---- 6. 等用户确认后再关闭浏览器 ----
        ev_close = threading.Event()
        with state_root.lock:
            state.close_browser_event = ev_close
            state.status = "waiting_close"
        bus.publish(
            "info",
            "⏳ 浏览器保留中。检查完成后点击"
            "「关闭浏览器」（页面右侧操作面板）即可释放资源。",
        )
        ev_close.wait()

        # ---- 7. 关闭浏览器 ----
        bus.publish("info", "👋 正在关闭浏览器...")
        try:
            registrar.close()
        except Exception as e:
            logger.warning(f"关闭浏览器异常: {e}")
        bus.publish("info", "✅ 浏览器已关闭")

        with state_root.lock:
            state.status = "done" if result else "error"
            state.error_msg = None if result else "注册失败"

    except Exception as e:
        logger.error(f"注册异常: {e}\n{traceback.format_exc()}")
        bus.publish("error", f"❌ 注册异常: {e}")
        with state_root.lock:
            state.status = "error"
            state.error_msg = str(e)
            # 异常时尽量关闭浏览器
            registrar = state.registrar
        if registrar is not None:
            try:
                registrar.close()
            except Exception:
                pass


# ============================== HTTP 端点 ==============================

@router.post("/start")
async def start_register() -> Dict[str, Any]:
    """开始注册任务（异步），返回任务初始状态"""
    state_root = get_state()
    state = state_root.register
    with state_root.lock:
        if state.thread and state.thread.is_alive():
            raise HTTPException(409, "已有注册任务在运行，请先停止或等待完成")
        state.reset()
        state.status = "running"
        t = threading.Thread(target=_register_worker, name="register-worker", daemon=True)
        state.thread = t
        t.start()
    return {"ok": True, "status": "running"}


@router.post("/stop")
async def stop_register() -> Dict[str, Any]:
    """停止注册任务（强制关闭浏览器）"""
    state_root = get_state()
    state = state_root.register
    bus = get_bus()
    with state_root.lock:
        registrar = state.registrar
        # 同时把所有等待的 event 都设掉，让 worker 线程能退出
        for ev in (state.confirm_event, state.confirm_success_event, state.close_browser_event):
            if ev:
                ev.set()
    if registrar is not None:
        try:
            registrar.close()
            bus.publish("warning", "⛔ 用户主动停止注册，浏览器已强制关闭")
        except Exception:
            pass
    with state_root.lock:
        state.status = "idle"
    return {"ok": True}


@router.post("/confirm")
async def confirm_action() -> Dict[str, Any]:
    """用户已完成验证码 / 手动操作，让 worker 继续往下跑"""
    state_root = get_state()
    state = state_root.register
    with state_root.lock:
        ev = state.confirm_event
    if not ev:
        raise HTTPException(409, "当前没有需要确认的操作")
    ev.set()
    return {"ok": True}


@router.post("/confirm-success")
async def confirm_success(req: ConfirmSuccessReq) -> Dict[str, Any]:
    """用户在控制台点了「✅ 注册成功」或「❌ 注册失败」"""
    state_root = get_state()
    state = state_root.register
    with state_root.lock:
        ev = state.confirm_success_event
        if not ev:
            raise HTTPException(409, "当前没有等待确认的注册结果")
        state.confirm_success_result = bool(req.success)
    ev.set()
    return {"ok": True, "success": req.success}


@router.post("/close-browser")
async def close_browser() -> Dict[str, Any]:
    """允许 worker 关闭浏览器（注册结束后会等用户点这个）"""
    state_root = get_state()
    state = state_root.register
    with state_root.lock:
        ev = state.close_browser_event
    if not ev:
        raise HTTPException(409, "当前没有等待关闭的浏览器")
    ev.set()
    return {"ok": True}


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """前端轮询用：返回当前注册任务的状态"""
    state_root = get_state()
    state = state_root.register
    with state_root.lock:
        return {
            "status": state.status,
            "email": state.email,
            "user_info": state.user_info,
            "error_msg": state.error_msg,
            # 等待中的提示文字
            "confirm_message": state.confirm_message if state.confirm_event else None,
            "confirm_success_message": (
                state.confirm_success_message if state.confirm_success_event else None
            ),
            "waiting_close": state.close_browser_event is not None,
        }
