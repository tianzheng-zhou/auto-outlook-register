# -*- coding: utf-8 -*-
"""
邮件监听 API
=============

- POST /api/monitor/start   启动监听（body: {email, password, interval, use_api}）
- POST /api/monitor/stop
- GET  /api/monitor/status
- GET  /api/monitor/emails  返回当前收集到的邮件列表

仅使用已有的 OutlookEmailMonitor / OutlookAPIMonitor。
"""
from __future__ import annotations

import threading
import time
import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import logger
from web.log_bus import get_bus
from web.state import get_state


router = APIRouter(prefix="/api/monitor", tags=["monitor"])


# 线程内收集到的邮件列表（最新在前）
_emails_store: List[Dict[str, Any]] = []
_emails_lock = threading.Lock()


class StartMonitorReq(BaseModel):
    email: str
    password: str
    interval: int = 30
    use_api: bool = False


def _monitor_worker(req: StartMonitorReq) -> None:
    """监听线程主体；逻辑对齐 PyQt MonitorWorker"""
    state_root = get_state()
    mstate = state_root.monitor
    bus = get_bus()

    def progress(msg: str) -> None:
        bus.publish("info", str(msg))

    # 简化：合并浏览器模式 / API 模式，用同一个入口
    try:
        progress("=" * 60)
        progress(f"🚀 开始监听邮箱: {req.email}")
        progress("=" * 60)

        if req.use_api:
            from core.outlook.token_manager import TokenManager
            from core.outlook.outlook_api_monitor import OutlookAPIMonitor

            tm = TokenManager()
            token = tm.load_token(req.email)
            if not token:
                progress("⚠️ 未找到 API token，退出")
                with state_root.lock:
                    mstate.status = "error"
                    mstate.error_msg = "未找到 API token"
                return

            monitor = OutlookAPIMonitor(req.email, token, progress_callback=progress)
            with state_root.lock:
                mstate.worker = monitor

            if not monitor.test_connection():
                progress("⚠️ API 连接失败，token 可能已过期")
                with state_root.lock:
                    mstate.status = "error"
                    mstate.error_msg = "API 连接失败"
                return

            # 初始
            progress("📬 获取邮件列表...")
            emails = monitor.get_latest_emails(count=10) or []
            _update_emails(emails)
            progress(f"✅ 初始 {len(emails)} 封邮件")

            last_count = len(emails)
            progress(f"⏰ 开始监听（每 {req.interval} 秒检查一次）")

            while mstate.is_running:
                time.sleep(req.interval)
                if not mstate.is_running:
                    break
                progress(f"🔄 [{time.strftime('%H:%M:%S')}] 检查新邮件")
                new_emails = monitor.get_latest_emails(count=10) or []
                if len(new_emails) > last_count:
                    progress(f"📨 发现 {len(new_emails) - last_count} 封新邮件")
                _update_emails(new_emails)
                last_count = len(new_emails)

        else:
            from core.outlook.outlook_monitor import OutlookEmailMonitor

            monitor = OutlookEmailMonitor(req.email, req.password, progress_callback=progress)
            with state_root.lock:
                mstate.worker = monitor

            progress("🌐 启动浏览器...")
            if not monitor.start_browser():
                progress("❌ 浏览器启动失败")
                with state_root.lock:
                    mstate.status = "error"
                    mstate.error_msg = "浏览器启动失败"
                return

            progress("🔐 登录...")
            if not monitor.login():
                progress("❌ 登录失败")
                with state_root.lock:
                    mstate.status = "error"
                    mstate.error_msg = "登录失败"
                return

            progress("📬 获取邮件列表...")
            emails = monitor.get_latest_emails(count=10) or []
            _update_emails(emails)
            last_count = len(emails)
            progress(f"✅ 初始 {last_count} 封邮件")

            while mstate.is_running:
                time.sleep(req.interval)
                if not mstate.is_running:
                    break
                progress(f"🔄 [{time.strftime('%H:%M:%S')}] 刷新并检查")
                try:
                    if monitor.driver:
                        monitor.driver.refresh()
                    time.sleep(3)
                    new_emails = monitor.get_latest_emails(count=10) or []
                    if len(new_emails) > last_count:
                        progress(f"📨 发现 {len(new_emails) - last_count} 封新邮件")
                    _update_emails(new_emails)
                    last_count = len(new_emails)
                except Exception as e:
                    progress(f"⚠️ 本次检查失败：{e}")

            # 退出前关浏览器
            try:
                monitor.close()
            except Exception:
                pass

        progress("✅ 监听已停止")
        with state_root.lock:
            mstate.status = "done"

    except Exception as e:
        logger.error(f"监听异常: {e}\n{traceback.format_exc()}")
        bus.publish("error", f"❌ 监听异常: {e}")
        with state_root.lock:
            mstate.status = "error"
            mstate.error_msg = str(e)
        try:
            w = mstate.worker
            if w and hasattr(w, "close"):
                w.close()
        except Exception:
            pass


def _update_emails(emails: List[Any]) -> None:
    """把 selenium/api monitor 返回的原始对象规范成 dict"""
    normalized = []
    for e in emails or []:
        if isinstance(e, dict):
            normalized.append({
                "from": e.get("sender") or e.get("from", ""),
                "subject": e.get("subject", ""),
                "date": e.get("time") or e.get("date", ""),
                "body": e.get("body", ""),
            })
    with _emails_lock:
        _emails_store.clear()
        _emails_store.extend(normalized)


@router.post("/start")
async def start_monitor(req: StartMonitorReq) -> Dict[str, Any]:
    state_root = get_state()
    mstate = state_root.monitor
    if not req.email or (not req.use_api and not req.password):
        raise HTTPException(400, "email 和 password 都必须提供（API 模式 password 可忽略）")
    with state_root.lock:
        if mstate.thread and mstate.thread.is_alive():
            raise HTTPException(409, "已有监听任务在运行")
        mstate.reset()
        mstate.status = "running"
        mstate.email = req.email
        mstate.is_running = True
        t = threading.Thread(target=_monitor_worker, args=(req,), name="monitor-worker", daemon=True)
        mstate.thread = t
        t.start()
    # 清空邮件缓存
    with _emails_lock:
        _emails_store.clear()
    return {"ok": True}


@router.post("/stop")
async def stop_monitor() -> Dict[str, Any]:
    state_root = get_state()
    mstate = state_root.monitor
    with state_root.lock:
        mstate.is_running = False
        w = mstate.worker
    if w and hasattr(w, "close"):
        try:
            w.close()
        except Exception:
            pass
    return {"ok": True}


@router.get("/status")
async def monitor_status() -> Dict[str, Any]:
    state_root = get_state()
    mstate = state_root.monitor
    with state_root.lock:
        return {
            "status": mstate.status,
            "email": mstate.email,
            "error_msg": mstate.error_msg,
            "is_running": mstate.is_running,
        }


@router.get("/emails")
async def list_emails() -> Dict[str, Any]:
    """返回当前线程抓到的邮件列表快照"""
    with _emails_lock:
        return {"ok": True, "count": len(_emails_store), "items": list(_emails_store)}
