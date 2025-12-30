"""
注册器基类 - 定义注册流程的抽象接口

使用工厂模式，支持扩展到其他平台（Cursor, GitHub Copilot等）
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from enum import Enum

from utils.logger import logger


class RegisterStatus(Enum):
    """注册状态枚举"""
    IDLE = "idle"
    FILLING_FORM = "filling_form"
    WAITING_CAPTCHA = "waiting_captcha"
    EXTRACTING_INFO = "extracting_info"
    BINDING_CARD = "binding_card"
    SUCCESS = "success"
    FAILED = "failed"


class BaseRegister(ABC):
    """注册器基类"""
    
    def __init__(self):
        self.status = RegisterStatus.IDLE
        self.status_callback: Optional[Callable[[str], None]] = None
        self.log_callback: Optional[Callable[[str, str], None]] = None
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """设置状态回调"""
        self.status_callback = callback
    
    def set_log_callback(self, callback: Callable[[str, str], None]):
        """设置日志回调（level, message）"""
        self.log_callback = callback
    
    def update_status(self, status: RegisterStatus, message: str = ""):
        """更新状态"""
        self.status = status
        if self.status_callback:
            self.status_callback(f"{status.value}: {message}" if message else status.value)
        logger.info(f"[{self.__class__.__name__}] Status: {status.value} - {message}")
    
    def log(self, level: str, message: str):
        """记录日志"""
        if self.log_callback:
            self.log_callback(level, message)
        
        if level == "info":
            logger.info(f"[{self.__class__.__name__}] {message}")
        elif level == "error":
            logger.error(f"[{self.__class__.__name__}] {message}")
        elif level == "warning":
            logger.warning(f"[{self.__class__.__name__}] {message}")
        else:
            logger.debug(f"[{self.__class__.__name__}] {message}")
    
    @abstractmethod
    def start_register(self, email: str, user_info: Dict[str, Any]) -> bool:
        """
        开始注册流程
        
        Args:
            email: 邮箱地址
            user_info: 用户信息（姓名、地址等）
        
        Returns:
            bool: 是否成功启动注册流程
        """
        pass
    
    @abstractmethod
    def extract_account_info(self) -> Optional[Dict[str, Any]]:
        """
        提取账号信息
        
        Returns:
            Optional[Dict]: 账号信息字典，失败返回None
        """
        pass
    
    @abstractmethod
    def bind_card(self, card_info: Dict[str, Any], user_info: Dict[str, Any]) -> bool:
        """
        绑定卡片
        
        Args:
            card_info: 卡片信息（卡号、过期日期、CVV等）
            user_info: 用户信息（姓名、地址等）
        
        Returns:
            bool: 是否成功绑卡
        """
        pass
    
    @abstractmethod
    def stop(self):
        """停止注册流程"""
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """获取平台名称"""
        pass

