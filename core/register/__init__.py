"""
注册模块 - 支持多平台账号注册

使用工厂模式，支持扩展到其他平台
"""

from core.register.base_register import BaseRegister, RegisterStatus
from core.register.augment_register import AugmentRegister
from core.register.register_factory import RegisterFactory

__all__ = [
    'BaseRegister',
    'RegisterStatus',
    'AugmentRegister',
    'RegisterFactory',
]

