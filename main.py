#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Outlook 自动注册工具 - 主入口
"""
import sys
import multiprocessing
from PyQt6.QtWidgets import QApplication

from config.settings import Settings
from utils.logger import setup_logger
from gui.main_window import MainWindow


def main():
    """主函数"""
    # 初始化日志系统
    logger = setup_logger()
    logger.info("="*60)
    logger.info(f"{Settings.APP_NAME} v{Settings.APP_VERSION}")
    logger.info("="*60)

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName(Settings.APP_NAME)
    app.setApplicationVersion(Settings.APP_VERSION)

    # 设置应用样式
    app.setStyle('Fusion')

    # 创建主窗口
    window = MainWindow()
    window.show()

    logger.info("应用启动成功")

    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    # 🔥 关键修复：PyInstaller 打包必须加这个，防止无限循环启动
    multiprocessing.freeze_support()
    main()

