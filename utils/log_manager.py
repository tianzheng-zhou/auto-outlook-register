# -*- coding: utf-8 -*-
"""
账号日志管理模块
功能：为每个邮箱账号保存和管理独立的注册日志
"""
import os
import json
from pathlib import Path
from datetime import datetime
from config.settings import DATA_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class LogManager:
    """账号日志管理器"""

    # 日志目录
    LOGS_DIR = DATA_DIR / "account_logs"
    
    @classmethod
    def _ensure_logs_dir(cls):
        """确保日志目录存在"""
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _get_log_file(cls, email: str) -> Path:
        """获取指定邮箱的日志文件路径"""
        cls._ensure_logs_dir()
        # 使用邮箱作为文件名（替换@为_）
        safe_email = email.replace('@', '_').replace('.', '_')
        return cls.LOGS_DIR / f"{safe_email}.log"
    
    @classmethod
    def save_log(cls, email: str, log_lines: list) -> bool:
        """
        保存账号的注册日志
        
        Args:
            email: 邮箱地址
            log_lines: 日志行列表
        
        Returns:
            bool: 是否保存成功
        """
        try:
            log_file = cls._get_log_file(email)
            
            # 将日志行写入文件
            with open(log_file, 'w', encoding='utf-8') as f:
                for line in log_lines:
                    f.write(line + '\n')
            
            logger.info(f"账号日志已保存: {email} ({len(log_lines)} 行)")
            return True
        except Exception as e:
            logger.error(f"保存账号日志失败 ({email}): {e}")
            return False
    
    @classmethod
    def load_log(cls, email: str) -> list:
        """
        加载账号的注册日志
        
        Args:
            email: 邮箱地址
        
        Returns:
            list: 日志行列表
        """
        try:
            log_file = cls._get_log_file(email)
            
            if not log_file.exists():
                logger.debug(f"账号日志不存在: {email}")
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = [line.rstrip('\n') for line in f.readlines()]
            
            logger.info(f"账号日志已加载: {email} ({len(lines)} 行)")
            return lines
        except Exception as e:
            logger.error(f"加载账号日志失败 ({email}): {e}")
            return []
    
    @classmethod
    def append_log(cls, email: str, log_line: str) -> bool:
        """
        追加日志行到账号日志文件
        
        Args:
            email: 邮箱地址
            log_line: 日志行
        
        Returns:
            bool: 是否追加成功
        """
        try:
            log_file = cls._get_log_file(email)
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
            
            return True
        except Exception as e:
            logger.error(f"追加账号日志失败 ({email}): {e}")
            return False
    
    @classmethod
    def delete_log(cls, email: str) -> bool:
        """
        删除账号的日志文件
        
        Args:
            email: 邮箱地址
        
        Returns:
            bool: 是否删除成功
        """
        try:
            log_file = cls._get_log_file(email)
            
            if log_file.exists():
                log_file.unlink()
                logger.info(f"账号日志已删除: {email}")
            
            return True
        except Exception as e:
            logger.error(f"删除账号日志失败 ({email}): {e}")
            return False
    
    @classmethod
    def clear_all_logs(cls) -> bool:
        """
        清空所有账号日志
        
        Returns:
            bool: 是否清空成功
        """
        try:
            cls._ensure_logs_dir()
            
            for log_file in cls.LOGS_DIR.glob("*.log"):
                log_file.unlink()
            
            logger.info("所有账号日志已清空")
            return True
        except Exception as e:
            logger.error(f"清空账号日志失败: {e}")
            return False

