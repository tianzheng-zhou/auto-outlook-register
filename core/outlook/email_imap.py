"""
Outlook邮件IMAP监听模块
使用IMAP协议直接获取邮件，无需浏览器
"""

import imaplib
import email
from email.header import decode_header
import time
from datetime import datetime
from utils.logger import logger


class OutlookIMAPMonitor:
    """Outlook邮件IMAP监听器"""
    
    # Outlook IMAP服务器配置
    IMAP_SERVER = "outlook.office365.com"
    IMAP_PORT = 993
    
    def __init__(self, email_address, password, progress_callback=None):
        """初始化IMAP监听器
        
        Args:
            email_address: 邮箱地址
            password: 密码
            progress_callback: 进度回调函数
        """
        self.email_address = email_address
        self.password = password
        self.progress_callback = progress_callback
        self.imap = None
        self.is_running = False
        
    def _update_progress(self, message):
        """更新进度"""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)
    
    def connect(self):
        """连接到IMAP服务器"""
        try:
            self._update_progress(f"正在连接到 {self.IMAP_SERVER}...")
            
            # 创建IMAP连接
            self.imap = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
            
            self._update_progress("正在登录...")
            # 登录
            self.imap.login(self.email_address, self.password)
            
            self._update_progress("✅ 登录成功！")
            return True
            
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "AUTHENTICATIONFAILED" in error_msg:
                self._update_progress("❌ 登录失败：用户名或密码错误")
            else:
                self._update_progress(f"❌ IMAP错误：{error_msg}")
            return False
        except Exception as e:
            self._update_progress(f"❌ 连接失败：{str(e)}")
            return False
    
    def disconnect(self):
        """断开IMAP连接"""
        try:
            if self.imap:
                self.imap.logout()
                self._update_progress("已断开连接")
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
    
    def decode_str(self, s):
        """解码邮件头部字符串"""
        if s is None:
            return ""
        
        value, encoding = decode_header(s)[0]
        if isinstance(value, bytes):
            if encoding:
                try:
                    return value.decode(encoding)
                except:
                    return value.decode('utf-8', errors='ignore')
            else:
                return value.decode('utf-8', errors='ignore')
        return str(value)
    
    def get_email_body(self, msg):
        """获取邮件正文"""
        body = ""
        
        if msg.is_multipart():
            # 多部分邮件
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # 跳过附件
                if "attachment" in content_disposition:
                    continue
                
                # 获取文本内容
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            body = payload.decode(charset, errors='ignore')
                            break
                    except Exception as e:
                        logger.error(f"解析邮件正文失败: {e}")
        else:
            # 单部分邮件
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='ignore')
            except Exception as e:
                logger.error(f"解析邮件正文失败: {e}")
        
        return body
    
    def fetch_emails(self, folder="INBOX", limit=10):
        """获取邮件列表
        
        Args:
            folder: 邮箱文件夹，默认收件箱
            limit: 获取邮件数量限制
            
        Returns:
            list: 邮件列表，每个元素是字典 {subject, from, date, body}
        """
        try:
            # 选择邮箱文件夹
            self.imap.select(folder)
            
            # 搜索所有邮件
            status, messages = self.imap.search(None, "ALL")
            
            if status != "OK":
                self._update_progress("❌ 搜索邮件失败")
                return []
            
            # 获取邮件ID列表
            email_ids = messages[0].split()
            
            if not email_ids:
                self._update_progress("📭 收件箱为空")
                return []
            
            # 获取最新的N封邮件
            email_ids = email_ids[-limit:]
            
            emails = []
            
            for email_id in reversed(email_ids):  # 从新到旧
                try:
                    # 获取邮件
                    status, msg_data = self.imap.fetch(email_id, "(RFC822)")
                    
                    if status != "OK":
                        continue
                    
                    # 解析邮件
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # 提取邮件信息
                    subject = self.decode_str(msg.get("Subject", ""))
                    from_addr = self.decode_str(msg.get("From", ""))
                    date_str = msg.get("Date", "")
                    
                    # 解析日期
                    try:
                        date_tuple = email.utils.parsedate_tz(date_str)
                        if date_tuple:
                            timestamp = email.utils.mktime_tz(date_tuple)
                            date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            date = date_str
                    except:
                        date = date_str
                    
                    # 获取邮件正文
                    body = self.get_email_body(msg)
                    
                    emails.append({
                        "subject": subject,
                        "from": from_addr,
                        "date": date,
                        "body": body[:500]  # 只取前500字符
                    })
                    
                except Exception as e:
                    logger.error(f"解析邮件失败: {e}")
                    continue
            
            self._update_progress(f"✅ 获取到 {len(emails)} 封邮件")
            return emails
            
        except Exception as e:
            self._update_progress(f"❌ 获取邮件失败：{str(e)}")
            return []
    
    def monitor(self, interval=30, callback=None):
        """持续监听新邮件
        
        Args:
            interval: 检查间隔（秒）
            callback: 新邮件回调函数
        """
        self.is_running = True
        last_count = 0
        
        try:
            while self.is_running:
                try:
                    # 选择收件箱
                    self.imap.select("INBOX")
                    
                    # 获取邮件数量
                    status, messages = self.imap.search(None, "ALL")
                    
                    if status == "OK":
                        email_ids = messages[0].split()
                        current_count = len(email_ids)
                        
                        if last_count == 0:
                            last_count = current_count
                            self._update_progress(f"📬 当前收件箱有 {current_count} 封邮件")
                        elif current_count > last_count:
                            new_count = current_count - last_count
                            self._update_progress(f"🔔 收到 {new_count} 封新邮件！")
                            
                            # 获取新邮件
                            new_emails = self.fetch_emails(limit=new_count)
                            
                            if callback:
                                callback(new_emails)
                            
                            last_count = current_count
                    
                    # 等待下次检查
                    self._update_progress(f"⏰ {interval}秒后再次检查...")
                    time.sleep(interval)
                    
                except Exception as e:
                    self._update_progress(f"⚠️ 监听出错：{str(e)}")
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            self._update_progress("⏹ 停止监听")
        finally:
            self.is_running = False
    
    def stop(self):
        """停止监听"""
        self.is_running = False

