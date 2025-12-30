# -*- coding: utf-8 -*-
"""
全局配置文件
"""
import os
import sys
from pathlib import Path

# 项目根目录（兼容 PyInstaller 打包）
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的应用
    import platform
    system = platform.system()

    # 数据目录：使用用户的应用支持目录
    if system == "Darwin":  # macOS
        BASE_DIR = Path.home() / "Library" / "Application Support" / "OutlookRegister"
    elif system == "Windows":
        BASE_DIR = Path(os.getenv('APPDATA', Path.home())) / "OutlookRegister"
    else:  # Linux
        BASE_DIR = Path.home() / ".config" / "OutlookRegister"

    # 资源目录：PyInstaller打包后的临时目录（包含chromedriver等资源）
    RESOURCE_DIR = Path(sys._MEIPASS)
else:
    # 开发环境
    BASE_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = BASE_DIR

# 数据目录
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 账号文件路径
ACCOUNTS_FILE = DATA_DIR / "accounts.txt"

# 数据库路径
DATABASE_PATH = DATA_DIR / "outlook.db"

# ChromeDriver路径（从资源目录获取，打包后在app包内）
CHROMEDRIVER_PATH = RESOURCE_DIR / "config" / "chromedriver"


class Settings:
    """全局配置类"""

    # 应用信息
    APP_NAME = "Outlook 自动注册工具"
    APP_VERSION = "1.0.0"

    # Chrome配置
    CHROME_VERSION = 142  # Chrome主版本号
    CHROMEDRIVER_PATH = CHROMEDRIVER_PATH  # 本地chromedriver路径
    
    # 超时配置
    DEFAULT_TIMEOUT = 20  # 默认等待超时（秒）
    PAGE_LOAD_TIMEOUT = 30  # 页面加载超时（秒）
    
    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = LOGS_DIR / "app.log"

    # 文件路径
    ACCOUNTS_FILE = ACCOUNTS_FILE
    DATABASE_PATH = DATABASE_PATH

    # UI配置
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    
    @classmethod
    def get_chrome_options(cls):
        """获取Chrome配置选项"""
        return {
            'lang': 'zh-CN',
            'start_maximized': True,
            'disable_dev_shm_usage': True,
            'no_sandbox': True,
            'accept_languages': 'zh-CN,zh;q=0.9,en;q=0.8'
        }

