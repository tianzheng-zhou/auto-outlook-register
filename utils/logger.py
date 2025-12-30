# -*- coding: utf-8 -*-
"""
日志系统
"""
import logging
import sys
from pathlib import Path
from config.settings import Settings


def setup_logger(name="auto-ai-register", log_file=None, level=None):
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
        level: 日志级别
    
    Returns:
        logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = level or Settings.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level))
    
    # 创建格式化器
    formatter = logging.Formatter(Settings.LOG_FORMAT)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file is None:
        log_file = Settings.LOG_FILE
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name=None):
    """
    获取日志记录器

    Args:
        name: 日志记录器名称，如果为None则返回根记录器

    Returns:
        logger: 日志记录器
    """
    if name is None:
        name = "auto-ai-register"
    return logging.getLogger(name)


# 创建默认logger实例
logger = setup_logger()
