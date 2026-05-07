#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Outlook 自动注册工具 - 主入口

默认启动 Web 控制台（端口 28942）。
若想用旧版 PyQt 桌面 GUI 作为兜底：

    python main.py --gui

环境变量也支持：
    OUTLOOK_REG_GUI=1  python main.py    # 等同 --gui
"""
from __future__ import annotations

import argparse
import os
import sys
import multiprocessing
import threading
import webbrowser

from config.settings import Settings
from utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="outlook-register")
    p.add_argument("--gui", action="store_true",
                   help="启动旧版 PyQt 桌面 GUI（默认走 Web）")
    p.add_argument("--host", default="127.0.0.1",
                   help="Web 监听地址，默认 127.0.0.1")
    p.add_argument("--port", type=int, default=28942,
                   help="Web 监听端口，默认 28942")
    p.add_argument("--reload", action="store_true",
                   help="Web 模式开启 uvicorn 热重载（开发用）")
    p.add_argument("--no-browser", action="store_true",
                   help="启动后不自动打开浏览器")
    return p.parse_args()


def run_gui() -> None:
    """旧版 PyQt 桌面 GUI（兜底）"""
    from PyQt6.QtWidgets import QApplication
    from gui.main_window import MainWindow

    logger = setup_logger()
    logger.info("=" * 60)
    logger.info(f"{Settings.APP_NAME} v{Settings.APP_VERSION} (GUI 模式)")
    logger.info("=" * 60)

    app = QApplication(sys.argv)
    app.setApplicationName(Settings.APP_NAME)
    app.setApplicationVersion(Settings.APP_VERSION)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    logger.info("应用启动成功")
    sys.exit(app.exec())


def run_web(host: str, port: int, reload: bool, open_browser: bool) -> None:
    """默认入口：启动 FastAPI Web 服务器"""
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info(f"{Settings.APP_NAME} v{Settings.APP_VERSION} (Web 模式)")
    logger.info("=" * 60)
    logger.info(f"🌐 Web 控制台：http://{host}:{port}")

    if open_browser:
        # 等服务器起来再开浏览器
        threading.Timer(
            1.5, lambda: webbrowser.open(f"http://{host}:{port}")
        ).start()

    from web.server import run as run_uvicorn
    run_uvicorn(host=host, port=port, reload=reload)


def main() -> None:
    args = parse_args()
    use_gui = args.gui or bool(os.environ.get("OUTLOOK_REG_GUI"))

    if use_gui:
        run_gui()
    else:
        run_web(args.host, args.port, args.reload, not args.no_browser)


if __name__ == "__main__":
    # PyInstaller 打包必须加这个，防止子进程无限循环启动
    multiprocessing.freeze_support()
    main()
