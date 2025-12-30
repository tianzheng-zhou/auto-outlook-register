# -*- coding: utf-8 -*-
"""
Outlook API 模块 - 使用Microsoft Graph API拉取邮件
"""
import requests
import json
from typing import List, Dict, Optional
from utils.logger import logger


class OutlookAPI:
    """使用Microsoft Graph API访问Outlook邮件"""
    
    # Microsoft Graph API 端点
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, access_token: str, progress_callback=None):
        """
        初始化Outlook API
        
        Args:
            access_token: Microsoft Graph API 的访问令牌
            progress_callback: 进度回调函数
        """
        self.access_token = access_token
        self.progress_callback = progress_callback
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _update_progress(self, message: str):
        """更新进度"""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)
    
    def get_latest_emails(self, count: int = 10) -> List[Dict]:
        """
        获取最新的邮件列表
        
        Args:
            count: 获取邮件数量
            
        Returns:
            邮件列表
        """
        try:
            self._update_progress(f"📬 正在通过API获取最新 {count} 封邮件...")
            
            # 构建查询参数
            params = {
                "$top": count,
                "$orderby": "receivedDateTime desc",
                "$select": "id,from,subject,bodyPreview,receivedDateTime,body,isRead"
            }
            
            # 调用API
            url = f"{self.GRAPH_API_URL}/me/mailFolders/inbox/messages"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                self._update_progress(f"❌ API请求失败: {response.status_code}")
                self._update_progress(f"   错误信息: {response.text}")
                return []
            
            data = response.json()
            emails = []
            
            for i, msg in enumerate(data.get("value", [])):
                try:
                    email_data = {
                        "index": i + 1,
                        "sender": msg.get("from", {}).get("emailAddress", {}).get("name", "未知发件人"),
                        "subject": msg.get("subject", "无主题"),
                        "body": msg.get("body", {}).get("content", msg.get("bodyPreview", "")),
                        "time": msg.get("receivedDateTime", ""),
                        "is_read": msg.get("isRead", False),
                        "id": msg.get("id", "")
                    }
                    emails.append(email_data)
                except Exception as e:
                    self._update_progress(f"⚠️  解析第 {i+1} 封邮件失败: {str(e)}")
                    continue
            
            self._update_progress(f"✅ 获取到 {len(emails)} 封邮件")
            return emails
            
        except Exception as e:
            self._update_progress(f"❌ 获取邮件列表失败: {str(e)}")
            logger.error(f"API获取邮件失败: {e}")
            return []
    
    def get_email_body(self, email_id: str) -> str:
        """
        获取邮件完整内容
        
        Args:
            email_id: 邮件ID
            
        Returns:
            邮件内容
        """
        try:
            url = f"{self.GRAPH_API_URL}/me/messages/{email_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                msg = response.json()
                return msg.get("body", {}).get("content", "")
            else:
                return "（无法获取邮件内容）"
                
        except Exception as e:
            logger.error(f"获取邮件内容失败: {e}")
            return "（获取邮件内容出错）"
    
    def mark_as_read(self, email_id: str) -> bool:
        """
        标记邮件为已读
        
        Args:
            email_id: 邮件ID
            
        Returns:
            是否成功
        """
        try:
            url = f"{self.GRAPH_API_URL}/me/messages/{email_id}"
            data = {"isRead": True}
            response = requests.patch(url, headers=self.headers, json=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"标记邮件为已读失败: {e}")
            return False
    
    def delete_email(self, email_id: str) -> bool:
        """
        删除邮件
        
        Args:
            email_id: 邮件ID
            
        Returns:
            是否成功
        """
        try:
            url = f"{self.GRAPH_API_URL}/me/messages/{email_id}"
            response = requests.delete(url, headers=self.headers)
            return response.status_code == 204
        except Exception as e:
            logger.error(f"删除邮件失败: {e}")
            return False


class OutlookTokenExtractor:
    """从浏览器中提取Outlook认证令牌"""
    
    @staticmethod
    def extract_token_from_browser(driver) -> Optional[str]:
        """
        从Selenium WebDriver中提取访问令牌
        
        Args:
            driver: Selenium WebDriver实例
            
        Returns:
            访问令牌或None
        """
        try:
            # 尝试从localStorage中获取token
            token = driver.execute_script("""
                return localStorage.getItem('access_token') || 
                       sessionStorage.getItem('access_token') ||
                       localStorage.getItem('token');
            """)
            
            if token:
                return token
            
            # 尝试从cookies中获取
            cookies = driver.get_cookies()
            for cookie in cookies:
                if 'token' in cookie.get('name', '').lower():
                    return cookie.get('value')
            
            return None
            
        except Exception as e:
            logger.error(f"提取token失败: {e}")
            return None
    
    @staticmethod
    def extract_cookies_from_browser(driver) -> Dict:
        """
        从浏览器中提取所有cookies
        
        Args:
            driver: Selenium WebDriver实例
            
        Returns:
            cookies字典
        """
        try:
            cookies = {}
            for cookie in driver.get_cookies():
                cookies[cookie['name']] = cookie['value']
            return cookies
        except Exception as e:
            logger.error(f"提取cookies失败: {e}")
            return {}

