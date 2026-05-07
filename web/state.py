# -*- coding: utf-8 -*-
"""
全局后端状态
============

承载注册任务、监听任务的运行时状态。整个进程一个实例。
所有读写都通过 .lock 保证线程安全。
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional


class _RegisterState:
    """单次注册任务的状态"""

    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        # idle / running / waiting_confirm / waiting_confirm_success / waiting_close / done / error
        self.status: str = "idle"
        self.email: Optional[str] = None
        self.user_info: Dict[str, Any] = {}
        self.error_msg: Optional[str] = None

        # 阻塞等待的事件（worker 线程会 .wait()，前端通过 API 触发 .set()）
        self.confirm_event: Optional[threading.Event] = None
        self.confirm_message: str = ""
        self.confirm_success_event: Optional[threading.Event] = None
        self.confirm_success_message: str = ""
        self.confirm_success_result: bool = False
        self.close_browser_event: Optional[threading.Event] = None

        # 实际的 OutlookRegistration 实例，便于 stop / close
        self.registrar: Any = None

    def reset(self) -> None:
        self.thread = None
        self.status = "idle"
        self.email = None
        self.user_info = {}
        self.error_msg = None
        self.confirm_event = None
        self.confirm_message = ""
        self.confirm_success_event = None
        self.confirm_success_message = ""
        self.confirm_success_result = False
        self.close_browser_event = None
        self.registrar = None


class _MonitorState:
    """单次邮件监听任务的状态"""

    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        self.status: str = "idle"     # idle / running / done / error
        self.email: Optional[str] = None
        self.error_msg: Optional[str] = None
        self.worker: Any = None       # MonitorWorker 实例
        self.is_running: bool = False

    def reset(self) -> None:
        self.thread = None
        self.status = "idle"
        self.email = None
        self.error_msg = None
        self.worker = None
        self.is_running = False


class State:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.register = _RegisterState()
        self.monitor = _MonitorState()


_state = State()


def get_state() -> State:
    return _state
