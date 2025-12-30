# -*- coding: utf-8 -*-
"""
Token管理模块 - 负责Microsoft Graph API token的保存、加载、刷新
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict
from utils.logger import logger
from config.settings import Settings


class TokenManager:
    """管理Outlook API的访问令牌"""

    def __init__(self, token_dir: str = None):
        """
        初始化Token管理器

        Args:
            token_dir: token保存目录（如果为None，使用Settings中的DATA_DIR）
        """
        if token_dir is None:
            # 使用Settings中的数据目录
            self.token_dir = str(Settings.ACCOUNTS_FILE.parent / "tokens")
        else:
            self.token_dir = token_dir

        # 创建token目录
        token_path = Path(self.token_dir)
        token_path.mkdir(parents=True, exist_ok=True)
    
    def _get_token_file(self, email: str) -> str:
        """获取token文件路径"""
        # 使用邮箱作为文件名（去掉@后面的部分）
        safe_email = email.replace("@", "_").replace(".", "_")
        return os.path.join(self.token_dir, f"{safe_email}.json")
    
    def save_token(self, email: str, access_token: str, expires_in: int = 3600) -> bool:
        """
        保存token
        
        Args:
            email: 邮箱地址
            access_token: 访问令牌
            expires_in: token过期时间（秒），默认3600秒（1小时）
            
        Returns:
            是否保存成功
        """
        try:
            token_file = self._get_token_file(email)
            
            # 计算过期时间
            expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            token_data = {
                "email": email,
                "access_token": access_token,
                "expires_at": expires_at,
                "created_at": datetime.now().isoformat()
            }
            
            with open(token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2)
            
            logger.info(f"✅ Token已保存: {email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存token失败: {e}")
            return False
    
    def load_token(self, email: str) -> Optional[str]:
        """
        加载token
        
        Args:
            email: 邮箱地址
            
        Returns:
            访问令牌或None
        """
        try:
            token_file = self._get_token_file(email)
            
            if not os.path.exists(token_file):
                logger.warning(f"⚠️  Token文件不存在: {email}")
                return None
            
            with open(token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # 检查token是否过期
            expires_at = datetime.fromisoformat(token_data.get("expires_at", ""))
            if datetime.now() > expires_at:
                logger.warning(f"⚠️  Token已过期: {email}")
                self.delete_token(email)
                return None
            
            logger.info(f"✅ Token已加载: {email}")
            return token_data.get("access_token")
            
        except Exception as e:
            logger.error(f"❌ 加载token失败: {e}")
            return None
    
    def is_token_valid(self, email: str) -> bool:
        """
        检查token是否有效
        
        Args:
            email: 邮箱地址
            
        Returns:
            token是否有效
        """
        try:
            token_file = self._get_token_file(email)
            
            if not os.path.exists(token_file):
                return False
            
            with open(token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # 检查token是否过期
            expires_at = datetime.fromisoformat(token_data.get("expires_at", ""))
            
            # 如果还有5分钟就过期，也认为无效
            if datetime.now() > expires_at - timedelta(minutes=5):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 检查token失败: {e}")
            return False
    
    def delete_token(self, email: str) -> bool:
        """
        删除token
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否删除成功
        """
        try:
            token_file = self._get_token_file(email)
            
            if os.path.exists(token_file):
                os.remove(token_file)
                logger.info(f"✅ Token已删除: {email}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除token失败: {e}")
            return False
    
    def get_token_info(self, email: str) -> Optional[Dict]:
        """
        获取token信息
        
        Args:
            email: 邮箱地址
            
        Returns:
            token信息字典或None
        """
        try:
            token_file = self._get_token_file(email)
            
            if not os.path.exists(token_file):
                return None
            
            with open(token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            return token_data
            
        except Exception as e:
            logger.error(f"❌ 获取token信息失败: {e}")
            return None

