# -*- coding: utf-8 -*-
"""
SSE 日志总线
============

把后端 logger 的 record 和 print 输出统一捕获，推送给所有前端 SSE 订阅者。

工作机制：
- 每个 SSE 连接订阅时拿到一个 asyncio.Queue
- _BusHandler (logging.Handler) 把 'auto-ai-register' logger 的 record 推到所有 queue
- _PrintCapture 包装 sys.stdout/stderr，按行截取后推到所有 queue
- publish() 也可以被业务代码主动调用

支持跨线程（worker 线程通过 put_nowait 安全推送）。
"""
from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime
from queue import Queue, Empty, Full
from typing import List, Optional


class LogBus:
    """日志广播总线，所有 SSE 订阅者收到同一份消息"""

    def __init__(self) -> None:
        # 使用 threading.Queue 而不是 asyncio.Queue：
        # publish 会在非 asyncio 线程（worker 线程）被调用，threading.Queue 是线程安全的
        # SSE handler 在 asyncio loop 中用 run_in_executor 取 queue 即可
        self._queues: List[Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> Queue:
        q: Queue = Queue(maxsize=2000)
        with self._lock:
            self._queues.append(q)
        return q

    def unsubscribe(self, q: Queue) -> None:
        with self._lock:
            try:
                self._queues.remove(q)
            except ValueError:
                pass

    def publish(self, level: str, message: str) -> None:
        """向所有订阅者广播一行日志；非阻塞，队满会丢弃最旧一条"""
        with self._lock:
            queues = list(self._queues)
        if not queues:
            return
        line = {
            "ts": datetime.now().strftime("%H:%M:%S"),
            "level": (level or "info").upper(),
            "msg": message,
        }
        for q in queues:
            try:
                q.put_nowait(line)
            except Full:
                # 满了 → 丢一条最旧的，再放新的
                try:
                    q.get_nowait()
                except Empty:
                    pass
                try:
                    q.put_nowait(line)
                except Exception:
                    pass
            except Exception:
                pass


_bus = LogBus()


def get_bus() -> LogBus:
    return _bus


# =================== logging.Handler ===================
class _BusHandler(logging.Handler):
    """把 LogRecord 转发到 LogBus"""

    def __init__(self, bus: LogBus):
        super().__init__()
        self.bus = bus

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = record.levelname.lower()
            msg = self.format(record)
            self.bus.publish(level, msg)
        except Exception:
            # logging handler 内部异常一律静默
            pass


# =================== stdout/stderr 拦截 ===================
class _PrintCapture:
    """包装 sys.stdout/stderr，按行截取后推 bus，同时保留原始输出"""

    def __init__(self, bus: LogBus, original, level: str = "info"):
        self.bus = bus
        self.original = original
        self.level = level
        self._buffer = ""
        self._lock = threading.Lock()

    def write(self, s: str) -> int:
        # 1. 维持原始 stdout 输出（控制台仍能看到）
        try:
            self.original.write(s)
        except Exception:
            pass
        # 2. 行缓冲，整行才推
        try:
            with self._lock:
                self._buffer += s
                while "\n" in self._buffer:
                    line, self._buffer = self._buffer.split("\n", 1)
                    line = line.rstrip("\r")
                    if line:
                        self.bus.publish(self.level, line)
        except Exception:
            pass
        return len(s)

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass

    # 让 sys.stdout 仍兼容更多属性
    def isatty(self) -> bool:
        try:
            return self.original.isatty()
        except Exception:
            return False

    @property
    def encoding(self) -> str:
        try:
            return getattr(self.original, "encoding", "utf-8") or "utf-8"
        except Exception:
            return "utf-8"


_installed = False


def install_capture() -> None:
    """
    幂等安装：把 'auto-ai-register' logger 的所有 record + print 都接到 bus。
    多次调用是安全的。
    """
    global _installed
    if _installed:
        return
    bus = get_bus()

    # 1. logger handler
    target_logger = logging.getLogger("auto-ai-register")
    handler = _BusHandler(bus)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    target_logger.addHandler(handler)

    # 2. stdout / stderr 行抓取
    if not isinstance(sys.stdout, _PrintCapture):
        sys.stdout = _PrintCapture(bus, sys.stdout, level="info")
    if not isinstance(sys.stderr, _PrintCapture):
        sys.stderr = _PrintCapture(bus, sys.stderr, level="error")

    _installed = True
