# -*- coding: utf-8 -*-
"""
文件管理工具
"""
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from config.settings import Settings
from .logger import get_logger

logger = get_logger(__name__)

# 延迟导入，避免循环依赖
_db_manager = None

def get_db_manager():
    """获取数据库管理器（延迟导入）"""
    global _db_manager
    if _db_manager is None:
        try:
            from database.db_manager import DatabaseManager
            _db_manager = DatabaseManager()
        except Exception as e:
            logger.warning(f"无法初始化数据库管理器: {e}")
    return _db_manager


class FileManager:
    """文件管理器"""
    
    @staticmethod
    def save_account(user_info: Dict, status: str = "未注册") -> bool:
        """
        保存账号信息到数据库和文件

        Args:
            user_info: 用户信息字典
            status: 注册状态 ("未注册" 或 "已注册")

        Returns:
            bool: 是否保存成功
        """
        try:
            email = str(user_info.get('email', ''))
            password = str(user_info.get('password', ''))
            birth_year = str(user_info.get('birth_year', ''))
            birth_month = str(user_info.get('birth_month', ''))
            birth_day = str(user_info.get('birth_day', ''))
            birthday = f"{birth_year}-{birth_month}-{birth_day}"
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

            # 保存到数据库
            db_manager = get_db_manager()
            if db_manager:
                try:
                    db_manager.add_outlook_account(
                        email=email,
                        password=password,
                        birthday=birthday,
                        status=status
                    )
                    logger.info(f"账号已保存到数据库: {email} (状态: {status})")
                except Exception as e:
                    logger.warning(f"保存到数据库失败: {e}")

            # 同时保存到文件（保持向后兼容）
            with open(Settings.ACCOUNTS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"状态: {status}\n")
                f.write(f"邮箱: {email}\n")
                f.write(f"密码: {password}\n")
                f.write(f"生日: {birthday}\n")
                f.write(f"创建时间: {timestamp}\n")
                f.write("-" * 50 + "\n")

            logger.info(f"账号信息已保存: {email} (状态: {status})")
            return True
        except Exception as e:
            logger.error(f"保存账号信息失败: {e}")
            return False
    
    @staticmethod
    def update_account_status(email: str, new_status: str = "已注册") -> bool:
        """
        更新账号状态（数据库和文件）

        Args:
            email: 邮箱地址
            new_status: 新状态

        Returns:
            bool: 是否更新成功
        """
        try:
            # 更新数据库
            db_manager = get_db_manager()
            if db_manager:
                try:
                    db_manager.update_outlook_account_status(email, new_status)
                    logger.info(f"数据库中账号状态已更新: {email} -> {new_status}")
                except Exception as e:
                    logger.warning(f"更新数据库状态失败: {e}")

            # 更新文件（保持向后兼容）
            if not Settings.ACCOUNTS_FILE.exists():
                logger.warning("账号文件不存在")
                return False

            with open(Settings.ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 找到对应邮箱的记录并更新状态
            updated_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                # 找到邮箱匹配的记录
                if line.startswith('邮箱:') and email in line:
                    # 回退到状态行
                    if i > 0 and updated_lines and updated_lines[-1].startswith('状态:'):
                        updated_lines[-1] = f"状态: {new_status}\n"
                updated_lines.append(line)
                i += 1

            # 写回文件
            with open(Settings.ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)

            logger.info(f"账号状态已更新: {email} -> {new_status}")
            return True
        except Exception as e:
            logger.error(f"更新账号状态失败: {e}")
            return False
    
    @staticmethod
    def load_accounts() -> List[Dict]:
        """
        加载所有账号信息（优先从数据库加载）

        Returns:
            List[Dict]: 账号信息列表
        """
        accounts = []

        try:
            # 优先从数据库加载
            db_manager = get_db_manager()
            if db_manager:
                try:
                    db_accounts = db_manager.get_all_outlook_accounts()
                    if db_accounts:
                        logger.info(f"从数据库加载了 {len(db_accounts)} 个账号")
                        return db_accounts
                except Exception as e:
                    logger.warning(f"从数据库加载账号失败: {e}")

            # 如果数据库为空或失败，从文件加载
            if not Settings.ACCOUNTS_FILE.exists():
                logger.info("账号文件不存在，返回空列表")
                return accounts

            with open(Settings.ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            current_account = {}
            for line in lines:
                line = line.strip()
                if line.startswith('状态:'):
                    if current_account:
                        accounts.append(current_account)
                    current_account = {'status': line.split(':', 1)[1].strip()}
                elif line.startswith('邮箱:'):
                    current_account['email'] = line.split(':', 1)[1].strip()
                elif line.startswith('密码:'):
                    current_account['password'] = line.split(':', 1)[1].strip()
                elif line.startswith('生日:'):
                    current_account['birthday'] = line.split(':', 1)[1].strip()
                elif line.startswith('创建时间:'):
                    current_account['created_at'] = line.split(':', 1)[1].strip()
                elif line.startswith('-' * 10):
                    if current_account:
                        accounts.append(current_account)
                        current_account = {}

            # 添加最后一个账号
            if current_account:
                accounts.append(current_account)

            logger.info(f"从文件加载了 {len(accounts)} 个账号")
            return accounts
        except Exception as e:
            logger.error(f"加载账号信息失败: {e}")
            return []


