"""
注册器工厂 - 根据平台类型创建对应的注册器

支持的平台：
- Augment
- Cursor (待实现)
- GitHub Copilot (待实现)
"""

from typing import Optional
from selenium import webdriver

from core.register.base_register import BaseRegister
from core.register.augment_register import AugmentRegister
from utils.logger import logger


class RegisterFactory:
    """注册器工厂"""
    
    # 支持的平台
    PLATFORMS = {
        'augment': AugmentRegister,
        # 'cursor': CursorRegister,  # 待实现
        # 'copilot': CopilotRegister,  # 待实现
    }
    
    @classmethod
    def create_register(cls, platform: str, driver: webdriver.Chrome) -> Optional[BaseRegister]:
        """
        创建注册器
        
        Args:
            platform: 平台名称 (augment, cursor, copilot)
            driver: Selenium WebDriver实例
        
        Returns:
            BaseRegister: 注册器实例，失败返回None
        """
        platform = platform.lower()
        
        if platform not in cls.PLATFORMS:
            logger.error(f"不支持的平台: {platform}")
            logger.info(f"支持的平台: {', '.join(cls.PLATFORMS.keys())}")
            return None
        
        register_class = cls.PLATFORMS[platform]
        try:
            register = register_class(driver)
            logger.info(f"创建注册器成功: {platform}")
            return register
        except Exception as e:
            logger.error(f"创建注册器失败: {e}")
            return None
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """获取支持的平台列表"""
        return list(cls.PLATFORMS.keys())

