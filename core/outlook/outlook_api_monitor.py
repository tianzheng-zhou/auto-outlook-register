# -*- coding: utf-8 -*-
"""
Outlook API 监听模块 - 使用Microsoft Graph SDK持续监听邮件
完全独立于浏览器方案，轻量级、高效
"""
import time
import requests
from typing import List, Dict, Optional
from utils.logger import logger

try:
    from msgraph.core import GraphClient
    from azure.identity import ClientSecretCredential
    MSGRAPH_SDK_AVAILABLE = True
except ImportError:
    MSGRAPH_SDK_AVAILABLE = False


class OutlookAPIMonitor:
    """使用Microsoft Graph API监听Outlook邮件"""

    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, email: str, access_token: str, progress_callback=None):
        """
        初始化API监听器

        Args:
            email: 邮箱地址
            access_token: Microsoft Graph API 的访问令牌
            progress_callback: 进度回调函数
        """
        self.email = email
        self.access_token = access_token
        self.progress_callback = progress_callback
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "outlook.body-content-type=html"  # 获取HTML格式的邮件内容
        }

        # 尝试使用msgraph-sdk
        self.use_sdk = False
        if MSGRAPH_SDK_AVAILABLE:
            try:
                # 创建GraphClient（使用Bearer token）
                from msgraph.core import GraphClient
                from msgraph_core import APIVersion

                # 使用自定义认证方式
                class BearerTokenAuth:
                    def __init__(self, token):
                        self.token = token

                    def __call__(self, request):
                        request.headers["Authorization"] = f"Bearer {self.token}"
                        return request

                self.graph_client = GraphClient(auth_provider=BearerTokenAuth(access_token))
                self.use_sdk = True
                self._update_progress("✅ 使用msgraph-sdk")
            except Exception as e:
                self._update_progress(f"⚠️  msgraph-sdk初始化失败: {str(e)[:50]}")
                self.use_sdk = False
    
    def _update_progress(self, message: str):
        """更新进度"""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)
    
    def test_connection(self) -> bool:
        """
        测试API连接

        Returns:
            连接是否成功
        """
        try:
            self._update_progress("🔗 测试API连接...")

            url = f"{self.GRAPH_API_URL}/me"
            self._update_progress(f"📍 调用API: GET {url}")
            self._update_progress(f"📍 请求头: Authorization: Bearer {self.access_token[:20]}...")

            response = requests.get(url, headers=self.headers, timeout=10)

            self._update_progress(f"📍 响应状态码: {response.status_code}")

            if response.status_code == 200:
                user_info = response.json()
                user_email = user_info.get("userPrincipalName", "")
                self._update_progress(f"✅ API连接成功: {user_email}")
                return True
            else:
                self._update_progress(f"❌ API连接失败: {response.status_code}")
                self._update_progress(f"📍 响应内容: {response.text[:200]}")
                return False

        except Exception as e:
            self._update_progress(f"❌ API连接异常: {str(e)}")
            return False
    
    def get_latest_emails(self, count: int = 10) -> List[Dict]:
        """
        获取最新的邮件列表（包含完整内容）

        Args:
            count: 获取邮件数量

        Returns:
            邮件列表
        """
        try:
            self._update_progress(f"📬 正在通过API获取最新 {count} 封邮件...")

            # 构建查询参数 - 确保获取完整的body内容
            params = {
                "$top": count,
                "$orderby": "receivedDateTime desc",
                "$select": "id,from,subject,bodyPreview,receivedDateTime,body,isRead,hasAttachments"
            }

            # 调用API
            url = f"{self.GRAPH_API_URL}/me/mailFolders/inbox/messages"
            self._update_progress(f"📍 调用API: GET {url}")
            self._update_progress(f"📍 查询参数: {params}")

            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            self._update_progress(f"📍 响应状态码: {response.status_code}")

            if response.status_code != 200:
                self._update_progress(f"❌ API请求失败: {response.status_code}")
                self._update_progress(f"📍 响应内容: {response.text[:200]}")
                return []

            data = response.json()
            self._update_progress(f"📍 API返回 {len(data.get('value', []))} 封邮件")

            emails = []

            for i, msg in enumerate(data.get("value", [])):
                try:
                    # 获取邮件内容 - 优先使用body.content，如果没有则使用bodyPreview
                    body_content = ""
                    if msg.get("body"):
                        body_content = msg.get("body", {}).get("content", "")
                        self._update_progress(f"📍 邮件#{i+1}: 从body.content获取内容 (长度: {len(body_content)})")

                    # 如果body为空，尝试获取完整邮件内容
                    if not body_content:
                        body_content = msg.get("bodyPreview", "")
                        if body_content:
                            self._update_progress(f"📍 邮件#{i+1}: 从bodyPreview获取内容 (长度: {len(body_content)})")

                        # 如果还是空，单独请求这封邮件的完整内容
                        if not body_content:
                            self._update_progress(f"📍 邮件#{i+1}: 单独请求完整内容...")
                            full_email = self.get_email_body(msg.get("id", ""))
                            body_content = full_email if full_email else "(无法获取邮件内容)"

                    email_data = {
                        "index": i + 1,
                        "sender": msg.get("from", {}).get("emailAddress", {}).get("name", "未知发件人"),
                        "subject": msg.get("subject", "无主题"),
                        "body": body_content,
                        "time": msg.get("receivedDateTime", ""),
                        "is_read": msg.get("isRead", False),
                        "id": msg.get("id", ""),
                        "has_attachments": msg.get("hasAttachments", False)
                    }
                    emails.append(email_data)
                except Exception as e:
                    self._update_progress(f"⚠️  解析第 {i+1} 封邮件失败: {str(e)[:100]}")
                    continue

            self._update_progress(f"✅ 获取到 {len(emails)} 封邮件")
            return emails

        except Exception as e:
            self._update_progress(f"❌ 获取邮件列表失败: {str(e)[:100]}")
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
            # 使用$select确保获取body字段
            url = f"{self.GRAPH_API_URL}/me/messages/{email_id}"
            params = {
                "$select": "body,bodyPreview"
            }
            self._update_progress(f"📍 调用API获取邮件内容: GET {url}")
            self._update_progress(f"📍 查询参数: {params}")

            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            self._update_progress(f"📍 响应状态码: {response.status_code}")

            if response.status_code == 200:
                msg = response.json()
                # 优先使用body.content，如果没有则使用bodyPreview
                body_content = msg.get("body", {}).get("content", "")
                if not body_content:
                    body_content = msg.get("bodyPreview", "")
                    self._update_progress(f"📍 使用bodyPreview (长度: {len(body_content)})")
                else:
                    self._update_progress(f"📍 使用body.content (长度: {len(body_content)})")

                return body_content if body_content else "（邮件内容为空）"
            else:
                self._update_progress(f"❌ 获取邮件内容失败: {response.status_code}")
                self._update_progress(f"📍 响应内容: {response.text[:200]}")
                logger.warning(f"获取邮件内容失败: {response.status_code}")
                return "（无法获取邮件内容）"

        except Exception as e:
            self._update_progress(f"❌ 获取邮件内容异常: {str(e)[:100]}")
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
            response = requests.patch(url, headers=self.headers, json=data, timeout=10)
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
            response = requests.delete(url, headers=self.headers, timeout=10)
            return response.status_code == 204
        except Exception as e:
            logger.error(f"删除邮件失败: {e}")
            return False

