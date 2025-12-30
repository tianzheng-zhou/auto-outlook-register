# -*- coding: utf-8 -*-
"""
Outlook 邮件监听模块
功能：登录 Outlook 账号，监听并获取最新邮件内容
"""
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.settings import Settings
from utils.logger import get_logger
from core.outlook.token_manager import TokenManager
from core.proxy import create_stealth_browser

logger = get_logger(__name__)


class OutlookEmailMonitor:
    def __init__(self, email, password, progress_callback=None):
        """
        初始化邮件监听器

        Args:
            email: Outlook 邮箱地址
            password: 邮箱密码
            progress_callback: 进度回调函数
        """
        self.email = email
        self.password = password
        self.progress_callback = progress_callback
        self.driver = None
        self.token_manager = TokenManager()  # 初始化token管理器

    def _update_progress(self, message):
        """更新进度"""
        print(message)  # 保留控制台输出
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)
        
    def _find_chrome_path(self):
        """查找Chrome浏览器路径"""
        import platform

        system = platform.system()
        chrome_paths = []

        if system == "Darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/usr/local/bin/google-chrome",
                "/usr/bin/google-chrome",
            ]
        elif system == "Windows":
            chrome_paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Users\\{}\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe".format(os.getenv('USERNAME', '')),
            ]
        elif system == "Linux":
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
            ]

        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"找到Chrome浏览器: {path}")
                return path

        logger.warning("未找到Chrome浏览器路径")
        return None

    def start_browser(self):
        """启动浏览器 - 使用完整的指纹伪装配置"""
        try:
            self._update_progress("🚀 启动 undetected-chromedriver...")

            # 尝试查找Chrome路径
            chrome_path = self._find_chrome_path()
            if chrome_path:
                self._update_progress(f"📍 使用Chrome路径: {chrome_path}")

            # 检查本地chromedriver是否存在
            driver_path = None
            if Settings.CHROMEDRIVER_PATH and Settings.CHROMEDRIVER_PATH.exists():
                driver_path = str(Settings.CHROMEDRIVER_PATH)
                self._update_progress(f"✅ 找到本地chromedriver: {driver_path}")
            else:
                self._update_progress("⚠️  本地chromedriver不存在，将自动下载（可能遇到SSL错误）")

            # 使用公共的浏览器指纹伪装函数
            try:
                self.driver = create_stealth_browser(
                    chrome_version=Settings.CHROME_VERSION,
                    headless=False,
                    driver_executable_path=driver_path
                )
                self._update_progress("✅ 浏览器启动成功")
                return True
            except Exception as e:
                logger.error(f"创建Chrome驱动失败: {e}", exc_info=True)
                self._update_progress(f"❌ 创建Chrome驱动失败: {e}")
                self._update_progress("⚠️  请确保已安装Google Chrome浏览器")
                return False

        except Exception as e:
            logger.error(f"浏览器启动异常: {e}", exc_info=True)
            self._update_progress(f"❌ 浏览器启动失败: {e}")
            return False
    
    def login(self):
        """登录 Outlook - 处理新的OAuth2登录流程"""
        try:
            self._update_progress(f"🔐 正在登录邮箱: {self.email}")

            # 直接使用登录链接，跳过Microsoft官网
            # LinkID=2125442 是Outlook登录的固定ID
            login_url = "https://go.microsoft.com/fwlink/p/?LinkID=2125442&deeplink=mail%2F0%2F%3Fnlp%3D0"
            self._update_progress(f"🌐 直接打开登录页面...")
            self.driver.get(login_url)
            time.sleep(2)  # 减少等待时间

            # 检查当前URL
            current_url = self.driver.current_url
            self._update_progress(f"📍 当前URL: {current_url[:80]}...")

            # === 1. 输入邮箱 ===
            self._update_progress("📧 正在输入邮箱地址...")

            # 等待邮箱输入框出现 - 尝试多个定位器
            email_input_locators = [
                (By.ID, "i0116"),  # 旧版本的ID
                (By.NAME, "loginfmt"),  # 通过name属性
                (By.CSS_SELECTOR, "input[type='email']"),  # CSS选择器
                (By.XPATH, "//input[@type='email']"),  # XPath
            ]

            email_input = None
            for locator in email_input_locators:
                try:
                    email_input = WebDriverWait(self.driver, 3).until(  # 减少等待时间到3秒
                        EC.presence_of_element_located(locator)
                    )
                    self._update_progress(f"✅ 找到邮箱输入框: {locator}")
                    break
                except:
                    continue

            if not email_input:
                self._update_progress("❌ 无法找到邮箱输入框")
                self._update_progress(f"📍 当前URL: {self.driver.current_url}")
                return False

            # 输入邮箱
            try:
                email_input.clear()
                email_input.send_keys(self.email)
                self._update_progress(f"✅ 邮箱输入成功: {self.email}")
            except Exception as e:
                self._update_progress(f"❌ 邮箱输入失败: {str(e)}")
                return False

            time.sleep(0.5)  # 减少等待时间

            # 点击下一步按钮 - 尝试多个定位器
            self._update_progress("🔘 点击'下一步'按钮...")
            next_btn_locators = [
                (By.CSS_SELECTOR, "button[data-testid='primaryButton']"),  # 新版本
                (By.ID, "idSIButton9"),  # 旧版本
                (By.CSS_SELECTOR, "button[type='submit']"),  # 通用提交按钮
            ]

            next_btn_found = False
            for locator in next_btn_locators:
                try:
                    next_btn = WebDriverWait(self.driver, 3).until(  # 减少等待时间到3秒
                        EC.element_to_be_clickable(locator)
                    )
                    next_btn.click()
                    self._update_progress(f"✅ 已点击下一步: {locator}")
                    next_btn_found = True
                    break
                except:
                    continue

            if not next_btn_found:
                self._update_progress("❌ 无法点击下一步按钮")
                return False

            time.sleep(2)  # 减少等待时间
            
            # === 2. 输入密码 ===
            self._update_progress("🔑 正在输入密码...")

            # 等待密码输入框出现 - 尝试多个ID（因为Microsoft经常改变ID）
            password_input_locators = [
                (By.ID, "passwordEntry"),  # 新版本的ID
                (By.ID, "i0118"),  # 旧版本的ID
                (By.NAME, "passwd"),  # 通过name属性
                (By.CSS_SELECTOR, "input[type='password']"),  # CSS选择器
            ]

            password_input = None
            for locator in password_input_locators:
                try:
                    password_input = WebDriverWait(self.driver, 3).until(  # 减少等待时间到3秒
                        EC.presence_of_element_located(locator)
                    )
                    self._update_progress(f"✅ 找到密码输入框: {locator}")
                    break
                except:
                    continue

            if not password_input:
                self._update_progress("❌ 无法找到密码输入框")
                self._update_progress(f"📍 当前URL: {self.driver.current_url}")
                return False

            # 输入密码
            try:
                password_input.clear()
                password_input.send_keys(self.password)
                self._update_progress("✅ 密码输入成功")
            except Exception as e:
                self._update_progress(f"❌ 密码输入失败: {str(e)}")
                return False

            time.sleep(0.5)  # 减少等待时间

            # 点击下一步/登录按钮 - 尝试多个定位器
            self._update_progress("🔘 点击'下一步'按钮...")
            submit_btn_locators = [
                (By.CSS_SELECTOR, "button[data-testid='primaryButton']"),  # 新版本
                (By.ID, "idSIButton9"),  # 旧版本
                (By.CSS_SELECTOR, "button[type='submit']"),  # 通用提交按钮
            ]

            submit_btn_found = False
            for locator in submit_btn_locators:
                try:
                    submit_btn = WebDriverWait(self.driver, 3).until(  # 减少等待时间到3秒
                        EC.element_to_be_clickable(locator)
                    )
                    submit_btn.click()
                    self._update_progress(f"✅ 已点击下一步: {locator}")
                    submit_btn_found = True
                    break
                except:
                    continue

            if not submit_btn_found:
                self._update_progress("❌ 无法点击下一步按钮")
                return False

            time.sleep(2)  # 减少等待时间

            # === 3. 处理确认页面（可能有多个） ===
            self._update_progress("🔍 处理登录后的确认页面...")

            # 需要处理多个确认页面，每个都点击"否"跳过
            max_confirmations = 3  # 最多处理3个确认页面
            confirmations_handled = 0

            for i in range(max_confirmations):
                try:
                    # 尝试找到"否"按钮
                    no_btn = WebDriverWait(self.driver, 2).until(  # 减少等待时间到2秒
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='secondaryButton']"))
                    )
                    no_btn.click()
                    confirmations_handled += 1
                    self._update_progress(f"✅ 已点击'否'跳过确认页面 #{confirmations_handled}")
                    time.sleep(1)  # 减少等待时间
                except:
                    # 没有找到"否"按钮，说明已经处理完所有确认页面
                    self._update_progress(f"ℹ️  已处理 {confirmations_handled} 个确认页面")
                    break

            # === 4. 验证登录成功 ===
            self._update_progress("🔍 验证登录状态...")
            time.sleep(1)  # 减少等待时间

            current_url = self.driver.current_url
            self._update_progress(f"📍 当前URL: {current_url[:100]}...")

            # 检查是否成功登录到Outlook
            # 登录成功的标志：URL包含outlook.live.com或outlook.office.com
            if "outlook.live.com" in current_url or "outlook.office.com" in current_url or "mail" in current_url:
                self._update_progress("✅ 登录成功！")

                # 尝试提取token（后台操作，不影响主流程）
                self._extract_and_save_token()

                return True
            else:
                self._update_progress(f"⚠️  当前页面: {current_url}")
                # 再等待一下，可能还在加载
                time.sleep(15)
                current_url = self.driver.current_url
                self._update_progress(f"📍 重新检查URL: {current_url[:100]}...")

                if "outlook.live.com" in current_url or "outlook.office.com" in current_url or "mail" in current_url:
                    self._update_progress("✅ 登录成功！")

                    # 尝试提取token（后台操作，不影响主流程）
                    self._extract_and_save_token()

                    return True
                else:
                    self._update_progress("❌ 登录可能失败，请检查")
                    return False

        except Exception as e:
            self._update_progress(f"❌ 登录失败: {str(e)}")
            logger.error(f"登录异常: {e}")
            return False
    
    def get_latest_emails(self, count=5):
        """
        获取最新的邮件列表（包含完整内容）

        Args:
            count: 获取邮件数量（默认 5 封）

        Returns:
            list: 邮件列表，每个元素包含 {sender, subject, body, time}
        """
        try:
            self._update_progress(f"\n📬 正在获取最新 {count} 封邮件...")
            time.sleep(0.5)  # 减少等待时间

            # 查找邮件列表项
            email_item_locators = [
                (By.CSS_SELECTOR, "div[role='listitem']"),
                (By.CSS_SELECTOR, "div[data-convid]"),
                (By.XPATH, "//div[@role='listitem']"),
            ]

            email_items = []
            for locator in email_item_locators:
                try:
                    email_items = self.driver.find_elements(*locator)
                    if email_items:
                        self._update_progress(f"✅ 使用定位器找到邮件列表: {locator}")
                        break
                except:
                    continue

            if not email_items:
                self._update_progress("📭 收件箱为空或未找到邮件列表")
                return []

            self._update_progress(f"✅ 找到 {len(email_items)} 封邮件")

            emails = []
            for i, item in enumerate(email_items[:count]):
                try:
                    # 提取邮件信息
                    email_data = {
                        "index": i + 1,
                        "sender": "未知发件人",
                        "subject": "无主题",
                        "body": "",
                        "time": ""
                    }

                    # 尝试获取发件人
                    try:
                        sender_elem = item.find_element(By.CSS_SELECTOR, "span[title]")
                        email_data["sender"] = sender_elem.get_attribute("title") or sender_elem.text
                    except:
                        pass

                    # 尝试获取主题
                    try:
                        subject_elem = item.find_element(By.CSS_SELECTOR, "span[data-convsubject]")
                        email_data["subject"] = subject_elem.text
                    except:
                        pass

                    # 尝试获取时间
                    try:
                        time_elem = item.find_element(By.CSS_SELECTOR, "span[aria-label*='时间']")
                        email_data["time"] = time_elem.get_attribute("aria-label") or time_elem.text
                    except:
                        pass

                    # 点击邮件获取完整内容
                    try:
                        item.click()
                        time.sleep(0.5)  # 减少等待时间

                        # 等待邮件内容加载
                        WebDriverWait(self.driver, 3).until(  # 减少等待时间到3秒
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='article']"))
                        )

                        # 获取邮件完整内容
                        try:
                            body_elem = self.driver.find_element(By.CSS_SELECTOR, "div[role='article']")
                            email_data["body"] = body_elem.text
                        except:
                            # 如果找不到完整内容，尝试获取预览
                            try:
                                preview_elem = item.find_element(By.CSS_SELECTOR, "span[data-convpreview]")
                                email_data["body"] = preview_elem.text
                            except:
                                email_data["body"] = "（无法获取邮件内容）"

                        # 返回列表
                        self.driver.back()
                        time.sleep(0.5)  # 减少等待时间

                    except Exception as e:
                        self._update_progress(f"⚠️  获取第 {i+1} 封邮件内容失败: {str(e)[:50]}")
                        # 尝试获取预览作为备选
                        try:
                            preview_elem = item.find_element(By.CSS_SELECTOR, "span[data-convpreview]")
                            email_data["body"] = preview_elem.text
                        except:
                            email_data["body"] = "（无法获取邮件内容）"

                    emails.append(email_data)

                except Exception as e:
                    self._update_progress(f"⚠️  解析第 {i+1} 封邮件失败: {str(e)[:50]}")
                    continue

            return emails

        except Exception as e:
            self._update_progress(f"❌ 获取邮件列表失败: {str(e)}")
            return []
    
    def monitor_emails(self, interval=30, duration=300):
        """
        持续监听新邮件
        
        Args:
            interval: 检查间隔（秒），默认 30 秒
            duration: 监听时长（秒），默认 300 秒（5 分钟）
        """
        print(f"\n🔔 开始监听新邮件...")
        print(f"   检查间隔: {interval} 秒")
        print(f"   监听时长: {duration} 秒")
        print("=" * 70)
        
        start_time = time.time()
        last_email_count = 0
        
        while time.time() - start_time < duration:
            try:
                # 刷新页面
                self.driver.refresh()
                time.sleep(5)
                
                # 获取最新邮件
                emails = self.get_latest_emails(count=1)
                
                if emails:
                    current_count = len(emails)
                    
                    # 检测到新邮件
                    if current_count > last_email_count or last_email_count == 0:
                        print("\n" + "=" * 70)
                        print("📨 检测到新邮件！")
                        print("=" * 70)
                        
                        for email in emails:
                            print(f"\n📧 邮件 #{email['index']}")
                            print(f"   发件人: {email['sender']}")
                            print(f"   主题: {email['subject']}")
                            print(f"   预览: {email['preview'][:50]}..." if len(email['preview']) > 50 else f"   预览: {email['preview']}")
                            print(f"   时间: {email['time']}")
                        
                        last_email_count = current_count
                    else:
                        print(f"ℹ️  [{time.strftime('%H:%M:%S')}] 暂无新邮件")
                
                # 等待下次检查
                print(f"⏰ 等待 {interval} 秒后再次检查...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断监听")
                break
            except Exception as e:
                print(f"❌ 监听过程出错: {e}")
                time.sleep(interval)
        
        print("\n✅ 监听结束")

    def _extract_and_save_token(self):
        """
        从浏览器中提取token并保存
        这是后台操作，不影响主流程
        """
        try:
            self._update_progress("🔑 正在提取API token...")

            # 尝试从localStorage中获取token
            token = self.driver.execute_script("""
                return localStorage.getItem('access_token') ||
                       sessionStorage.getItem('access_token') ||
                       localStorage.getItem('token');
            """)

            if token:
                self._update_progress(f"📍 从localStorage找到token (长度: {len(token)})")
                # 保存token（默认1小时过期）
                if self.token_manager.save_token(self.email, token, expires_in=3600):
                    self._update_progress("✅ Token已提取并保存")
                    return True

            # 如果从storage中获取失败，尝试从cookies中获取
            self._update_progress("ℹ️  从localStorage中未找到token，尝试从cookies中获取...")
            cookies = self.driver.get_cookies()
            self._update_progress(f"📍 找到 {len(cookies)} 个cookies")

            # 打印所有cookie名称用于调试
            cookie_names = [c.get('name', '') for c in cookies]
            self._update_progress(f"📍 Cookie名称: {', '.join(cookie_names[:10])}...")

            # 尝试多种token来源
            token_sources = [
                'access_token',
                'token',
                'auth_token',
                'authorization',
                'bearer',
                'msal.token.keys',
                'msal_token',
                'MSAuth01',  # Microsoft特定的token
                'MSAuthToken',
                'MSAL.token',
            ]

            for cookie in cookies:
                cookie_name = cookie.get('name', '').lower()
                cookie_value = cookie.get('value', '')

                # 检查是否是token相关的cookie
                for token_source in token_sources:
                    if token_source.lower() in cookie_name:
                        self._update_progress(f"📍 找到可能的token cookie: {cookie.get('name')} (长度: {len(cookie_value)})")
                        if len(cookie_value) > 50:  # token通常很长
                            if self.token_manager.save_token(self.email, cookie_value, expires_in=3600):
                                self._update_progress(f"✅ Token已从cookies中提取并保存 ({cookie.get('name')})")
                                return True

                # 也检查值很长的cookie（可能是token）
                if len(cookie_value) > 200 and cookie_name not in ['wl_sd', 'wl_cv']:
                    self._update_progress(f"📍 找到长值cookie: {cookie.get('name')} (长度: {len(cookie_value)})")

            self._update_progress("⚠️  未能提取token，后续将使用浏览器方案")
            return False

        except Exception as e:
            self._update_progress(f"⚠️  提取token失败: {str(e)[:100]}")
            logger.error(f"提取token异常: {e}")
            return False

    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self._update_progress("\n👋 正在关闭浏览器...")
                self.driver.quit()
                self._update_progress("✅ 浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")


def main():
    """主函数"""
    print("=" * 70)
    print("          📧 Outlook 邮件监听脚本")
    print("=" * 70)
    
    # 配置账号信息
    EMAIL = "your_email@outlook.com"  # 修改为你的邮箱
    PASSWORD = "your_password"  # 修改为你的密码

    # 创建监听器
    monitor = OutlookEmailMonitor(email=EMAIL, password=PASSWORD)
    
    try:
        # 启动浏览器
        if not monitor.start_browser():
            return
        
        # 登录
        if not monitor.login():
            print("❌ 登录失败，退出程序")
            return
        
        # 获取最新邮件
        emails = monitor.get_latest_emails(count=5)
        if emails:
            print("\n" + "=" * 70)
            print("📬 最新邮件列表")
            print("=" * 70)
            for email in emails:
                print(f"\n📧 邮件 #{email['index']}")
                print(f"   发件人: {email['sender']}")
                print(f"   主题: {email['subject']}")
                print(f"   预览: {email['preview'][:50]}..." if len(email['preview']) > 50 else f"   预览: {email['preview']}")
                print(f"   时间: {email['time']}")
        
        # 询问是否开启监听
        print("\n" + "=" * 70)
        choice = input("是否开启邮件监听？(y/n): ").strip().lower()
        
        if choice == 'y':
            # 开启监听（每 30 秒检查一次，持续 5 分钟）
            monitor.monitor_emails(interval=30, duration=300)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
    finally:
        # 关闭浏览器
        monitor.close()


if __name__ == "__main__":
    main()

