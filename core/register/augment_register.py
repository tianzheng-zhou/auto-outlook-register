"""
Augment注册器实现 - 完整自动化
"""

import time
import hashlib
import base64
import secrets
import json
import threading
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.register.base_register import BaseRegister, RegisterStatus
from database.augment_db_manager import AugmentDBManager
from database.db_manager import DatabaseManager
from utils.logger import logger


class AugmentRegister(BaseRegister):
    """Augment注册器 - 完整自动化"""
    
    # OAuth配置（参考Chrome插件）
    AUTH_URL = "https://auth.augmentcode.com/authorize"
    CLIENT_ID = "v"  # 注意：插件里用的是"v"，不是长ID
    RESPONSE_TYPE = "code"
    
    def __init__(self, driver: webdriver.Chrome):
        super().__init__()
        self.driver = driver
        self.db = AugmentDBManager()
        self.email_db = DatabaseManager()  # 邮箱数据库
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None
        self.state: Optional[str] = None
        self.current_email: Optional[str] = None
        self.current_email_id: Optional[int] = None  # 当前邮箱ID
        self.current_account_id: Optional[int] = None
        self.verification_failed: bool = False
        self._stop_monitoring = False
    
    def get_platform_name(self) -> str:
        return "Augment"
    
    def stop(self):
        """停止注册"""
        self._stop_monitoring = True
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def _generate_pkce_params(self):
        """生成PKCE参数"""
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
        self.code_verifier = ''.join(secrets.choice(chars) for _ in range(43))

        sha256_hash = hashlib.sha256(self.code_verifier.encode()).digest()
        self.code_challenge = base64.urlsafe_b64encode(sha256_hash).decode().rstrip('=')

        self.state = secrets.token_urlsafe(16)
        self.log("info", f"✅ 生成PKCE参数 - State: {self.state[:10]}...")

    def start_register(self, email: str, user_info: Dict[str, Any]) -> bool:
        """开始注册流程 - 完全自动化"""
        try:
            self.current_email = email
            self._stop_monitoring = False
            self.verification_failed = False  # 重置验证失败标志
            self.update_status(RegisterStatus.FILLING_FORM, "正在打开注册页面...")
            self.log("info", f"📧 使用邮箱: {email}")

            # 获取邮箱ID（用于失败时删除）
            email_obj = self.email_db.get_all_emails(status='unused')
            for e in email_obj:
                if e.email == email:
                    self.current_email_id = e.id
                    break

            self._generate_pkce_params()

            # 构建URL（参考Chrome插件，只需要4个参数）
            params = {
                'response_type': self.RESPONSE_TYPE,
                'code_challenge': self.code_challenge,
                'client_id': self.CLIENT_ID,
                'state': self.state,
                'prompt': 'login'
            }
            auth_url = f"{self.AUTH_URL}?{urlencode(params)}"

            self.log("info", f"🌐 打开注册页面...")
            self.log("debug", f"📍 URL: {auth_url}")

            # 设置页面加载超时（10秒 - 更快的超时，因为页面可能有慢资源）
            self.driver.set_page_load_timeout(10)

            try:
                self.log("info", "⏳ 正在加载页面...")
                self.driver.get(auth_url)
                self.log("info", "✅ 页面加载完成")
            except Exception as e:
                # 页面可能已经部分加载，这是正常的
                self.log("info", f"⏳ 页面加载中（可能有慢资源）: {str(e)[:50]}...")
                time.sleep(1)
            finally:
                # 重置超时时间为默认值（不限制后续操作）
                self.driver.set_page_load_timeout(300)

            # 检查当前URL
            current_url = self.driver.current_url
            self.log("info", f"📄 当前URL: {current_url[:80]}...")

            self.log("info", "✅ 页面已加载，开始填写邮箱...")
            time.sleep(0.5)

            if not self._fill_email(email):
                return False

            self._start_full_automation()

            return True

        except Exception as e:
            self.log("error", f"❌ 启动注册失败: {e}")
            self.update_status(RegisterStatus.FAILED, str(e))
            return False

    def _fill_email(self, email: str) -> bool:
        """填写邮箱（完全使用JavaScript，参考Chrome插件）"""
        try:
            self.log("info", "🔍 查找邮箱输入框...")

            # 完全使用JavaScript查找和填写（参考插件：const emailInput = document.querySelector('input#username[name="username"]')）
            result = self.driver.execute_script("""
                const emailInput = document.querySelector('input#username[name="username"]');

                if (!emailInput) {
                    return { success: false, error: 'Email input not found' };
                }

                const email = arguments[0];

                // 填写邮箱（参考插件的fillInput函数）
                emailInput.focus();
                emailInput.value = email;

                emailInput.dispatchEvent(new Event('input', { bubbles: true }));
                emailInput.dispatchEvent(new Event('change', { bubbles: true }));
                emailInput.dispatchEvent(new Event('blur', { bubbles: true }));

                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(emailInput, email);
                emailInput.dispatchEvent(new Event('input', { bubbles: true }));

                return { success: true };
            """, email)

            if result and result.get('success'):
                self.log("info", f"✅ 已填写邮箱: {email}")
                time.sleep(0.5)
                self._try_trigger_captcha()
                return True
            else:
                self.log("error", f"❌ 未找到邮箱输入框: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            self.log("error", f"❌ 填写邮箱失败: {e}")
            return False

    def _try_trigger_captcha(self):
        """尝试触发人机验证 - 使用JavaScript"""
        try:
            self.log("info", "🤖 尝试触发人机验证...")

            # 使用JavaScript查找并点击验证框
            result = self.driver.execute_script("""
                const captchaSelectors = [
                    '.ulp-auth0-v2-captcha',
                    '#ulp-auth0-v2-captcha',
                    '[data-captcha-provider]',
                    'iframe[src*="turnstile"]',
                    'iframe[src*="challenges.cloudflare.com"]'
                ];

                for (const selector of captchaSelectors) {
                    const captcha = document.querySelector(selector);
                    if (captcha) {
                        try {
                            captcha.click();
                            return { success: true, selector: selector };
                        } catch (e) {
                            return { success: false, error: e.message };
                        }
                    }
                }

                return { success: false, error: 'No captcha element found' };
            """)

            if result and result.get('success'):
                self.log("info", f"✅ 找到并点击验证框: {result.get('selector')}")
            else:
                self.log("debug", f"未找到验证框: {result.get('error', 'Unknown')}")

        except Exception as e:
            self.log("warning", f"⚠️ 触发验证框失败（不影响流程）: {e}")

    def _start_full_automation(self):
        """启动完整自动化监听 - 根据URL判断页面类型"""
        self.log("info", "🚀 启动智能页面监听...")

        # 只启动一个主监听线程，根据URL判断当前页面
        threading.Thread(target=self._monitor_page_changes, daemon=True).start()

        self.log("info", "✅ 页面监听已启动")

    def _monitor_page_changes(self):
        """主监听线程 - 根据URL判断页面类型并执行对应逻辑（参考Chrome插件）"""
        self.log("info", "👀 开始监听页面变化...")

        last_url = ""
        last_page_type = ""

        while not self._stop_monitoring:
            try:
                current_url = self.driver.current_url

                # URL变化时，判断页面类型
                if current_url != last_url:
                    last_url = current_url
                    page_type = self._get_page_type(current_url)

                    if page_type != last_page_type:
                        last_page_type = page_type
                        self.log("info", f"📄 检测到页面变化: {page_type} - {current_url[:60]}...")

                        # 根据页面类型执行对应逻辑
                        if page_type == "auth_page":
                            self._handle_auth_page()
                        elif page_type == "verification_code_page":
                            self._handle_verification_code_page()
                        elif page_type == "completing_signup_page":
                            self._handle_completing_signup_page()
                        elif page_type == "onboard_page":
                            self._handle_onboard_page()
                        elif page_type == "auth_continue_page":
                            self._handle_auth_continue_page()

                time.sleep(0.5)

            except Exception as e:
                self.log("debug", f"监听页面变化中... {e}")
                time.sleep(0.5)

    def _get_page_type(self, url: str) -> str:
        """根据URL判断页面类型（参考Chrome插件）"""
        if '/auth/continue' in url or '/complete-signup' in url:
            return "auth_continue_page"
        elif '/onboard' in url:
            return "onboard_page"
        elif 'Completing signup' in self.driver.page_source:
            return "completing_signup_page"
        elif 'auth.augmentcode.com' in url or '/u/login' in url or '/u/signup' in url:
            # 进一步判断是登录页还是验证码页
            try:
                code_input = self.driver.execute_script("return document.querySelector('input#code[name=\"code\"]');")
                if code_input:
                    return "verification_code_page"
            except:
                pass
            return "auth_page"
        elif 'billing.augmentcode.com' in url:
            return "billing_page"
        else:
            return "unknown"

    def _handle_auth_page(self):
        """处理登录页面 - 填写邮箱并监听人机验证完成"""
        self.log("info", "🔐 进入登录页面，开始填写邮箱...")

        # 填写邮箱
        if not self._fill_email(self.current_email):
            self.log("error", "❌ 填写邮箱失败！")
            return

        self.log("info", "✅ 邮箱已填写，开始监听人机验证...")
        self.update_status(RegisterStatus.WAITING_CAPTCHA, "等待人机验证...")

        # 启动人机验证监听
        threading.Thread(target=self._monitor_captcha_on_auth_page, daemon=True).start()

    def _handle_verification_code_page(self):
        """处理验证码页面 - 监听验证码输入"""
        self.log("info", "🔢 进入验证码页面，开始监听验证码输入...")

        # 启动验证码监听
        threading.Thread(target=self._monitor_code_input_on_code_page, daemon=True).start()

    def _handle_completing_signup_page(self):
        """处理Completing signup页面 - 检测验证失败"""
        self.log("info", "⏳ 进入Completing signup页面，检测验证结果...")

        # 启动验证失败监听
        threading.Thread(target=self._monitor_verification_failure_on_completing_page, daemon=True).start()

    def _handle_onboard_page(self):
        """处理Onboard页面 - 监听Skip for now按钮"""
        self.log("info", "👋 进入Onboard页面，开始监听Skip for now按钮...")

        # 启动Skip按钮监听
        threading.Thread(target=self._monitor_skip_on_onboard_page, daemon=True).start()

    def _handle_auth_continue_page(self):
        """处理auth/continue页面 - 先检测验证失败，再提取账号信息"""
        self.log("info", "✅ 进入auth/continue页面，等待验证结果...")

        # 启动验证失败监听（在completing signup页面）
        threading.Thread(target=self._monitor_verification_failure_on_auth_continue_page, daemon=True).start()

    def _monitor_verification_failure_on_auth_continue_page(self):
        """在auth/continue页面监听验证失败（Completing signup页面）"""
        attempt = 0
        max_attempts = 60  # 30秒超时

        while not self._stop_monitoring and attempt < max_attempts:
            try:
                attempt += 1

                # 检查页面内容是否包含"Completing signup"和"Verification failed"
                has_failure = self.driver.execute_script("""
                    const pageText = document.body.textContent;

                    // 检查是否在Completing signup页面
                    if (pageText.includes('Completing signup')) {
                        // 检查是否有Verification failed错误
                        const errorBox = document.querySelector('.border-red-500, .text-red-100, [class*="error"]');
                        if (errorBox && errorBox.textContent.includes('Verification failed')) {
                            return true;
                        }
                    }

                    return false;
                """)

                if has_failure:
                    self.log("error", "❌ 检测到验证失败（Completing signup页面）！")
                    self._handle_verification_failure()
                    return

                # 如果30秒内没有检测到验证失败，说明验证成功，开始提取信息
                if attempt >= max_attempts:
                    self.log("info", "✅ 未检测到验证失败，开始提取账号信息...")
                    time.sleep(2)
                    result = self.extract_account_info()

                    if result:
                        self.log("info", "✅ 账号信息提取成功！")
                        self.update_status(RegisterStatus.SUCCESS, "注册成功")
                    else:
                        self.log("error", "❌ 账号信息提取失败")
                        self.update_status(RegisterStatus.FAILED, "提取信息失败")
                        # 提取失败也要重试
                        self._handle_verification_failure()

                    self._stop_monitoring = True
                    return

                if attempt % 10 == 0:
                    self.log("debug", f"等待验证结果... (attempt {attempt}/{max_attempts})")

            except Exception as e:
                if attempt % 20 == 0:
                    self.log("debug", f"监听验证结果中... {e}")

            time.sleep(0.5)

    def _monitor_captcha_on_auth_page(self):
        """在登录页监听人机验证完成"""
        attempt = 0
        max_attempts = 240  # 120秒超时

        while not self._stop_monitoring and attempt < max_attempts:
            try:
                attempt += 1

                # 检查是否还在登录页
                current_url = self.driver.current_url
                if not ('auth.augmentcode.com' in current_url or '/u/login' in current_url):
                    self.log("debug", "已离开登录页，停止人机验证监听")
                    break

                # 检查人机验证是否完成
                captcha_input = self.driver.execute_script("return document.querySelector('input[name=\"captcha\"]');")

                if captcha_input and self.driver.execute_script("return arguments[0].value;", captcha_input):
                    self.log("info", "✅ 人机验证完成！")
                    time.sleep(1)

                    # 查找并点击Continue按钮
                    continue_btn = self.driver.execute_script("return document.querySelector('button[type=\"submit\"][name=\"action\"]');")

                    if continue_btn and not self.driver.execute_script("return arguments[0].disabled;", continue_btn):
                        self.log("info", "🖱️ 自动点击Continue按钮...")
                        continue_btn.click()
                        self.log("info", "✅ Continue按钮已点击，等待页面跳转...")
                        self.update_status(RegisterStatus.EXTRACTING_INFO, "正在提交...")
                        break

                if attempt % 20 == 0:
                    self.log("debug", f"等待人机验证中... (attempt {attempt})")

            except Exception as e:
                if attempt % 40 == 0:
                    self.log("debug", f"监听人机验证中... {e}")

            time.sleep(0.5)

    def _monitor_code_input_on_code_page(self):
        """在验证码页面监听验证码输入"""
        attempt = 0
        max_attempts = 240  # 120秒超时
        code_detected = False  # 标记是否已检测到验证码
        code_detected_time = 0  # 检测到验证码的时间（attempt次数）
        max_wait_for_button = 20  # 检测到验证码后，最多等待10秒（20次 * 0.5秒）按钮变为可用

        while not self._stop_monitoring and attempt < max_attempts:
            try:
                attempt += 1

                # 检查验证码输入框
                code_input = self.driver.execute_script("return document.querySelector('input#code[name=\"code\"]');")

                if code_input:
                    code_value = self.driver.execute_script("return arguments[0].value;", code_input)

                    if code_value and len(code_value) >= 4:
                        # 只在第一次检测到验证码时打印日志
                        if not code_detected:
                            self.log("info", f"✅ 检测到验证码已输入: {code_value}")
                            code_detected = True
                            code_detected_time = attempt

                        # 查找并点击Continue按钮
                        continue_btn = self.driver.execute_script("return document.querySelector('button[type=\"submit\"][name=\"action\"]');")

                        if continue_btn:
                            is_disabled = self.driver.execute_script("return arguments[0].disabled;", continue_btn)

                            if not is_disabled:
                                self.log("info", "🖱️ 自动点击Continue按钮（验证码页面）...")
                                continue_btn.click()
                                self.log("info", "✅ Continue按钮已点击，等待验证结果...")
                                break
                            else:
                                # 按钮被禁用，检查是否超时
                                wait_time = attempt - code_detected_time
                                if wait_time >= max_wait_for_button:
                                    self.log("error", f"❌ 验证码输入后，Continue按钮一直被禁用（等待了{wait_time * 0.5}秒），可能验证码错误！")
                                    self.log("info", "🔄 清空验证码，等待重新输入...")

                                    # 清空验证码输入框
                                    self.driver.execute_script("arguments[0].value = '';", code_input)

                                    # 重置标记
                                    code_detected = False
                                    code_detected_time = 0
                                elif wait_time % 10 == 0:
                                    self.log("debug", f"等待Continue按钮变为可用... (已等待{wait_time * 0.5}秒)")
                    else:
                        # 验证码被清空，重置标记
                        code_detected = False
                        code_detected_time = 0

                if attempt % 20 == 0 and not code_detected:
                    self.log("debug", f"等待验证码输入中... (attempt {attempt})")

            except Exception as e:
                if attempt % 40 == 0:
                    self.log("debug", f"监听验证码输入中... {e}")

            time.sleep(0.5)

    def _monitor_verification_failure_on_completing_page(self):
        """在Completing signup页面监听验证失败"""
        attempt = 0
        max_attempts = 60  # 30秒超时

        while not self._stop_monitoring and attempt < max_attempts:
            try:
                attempt += 1

                # 检查是否有Verification failed错误
                error_box = self.driver.execute_script("""
                    const errorBox = document.querySelector('.border-red-500');
                    if (errorBox && errorBox.textContent.includes('Verification failed')) {
                        return true;
                    }
                    return false;
                """)

                if error_box:
                    self.log("error", "❌ 检测到验证失败（Completing signup页面）！")
                    self._handle_verification_failure()
                    break

            except Exception as e:
                if attempt % 20 == 0:
                    self.log("debug", f"监听验证失败中... {e}")

            time.sleep(0.5)

    def _monitor_skip_on_onboard_page(self):
        """在Onboard页面监听Skip for now按钮"""
        attempt = 0
        max_attempts = 120  # 60秒超时

        while not self._stop_monitoring and attempt < max_attempts:
            try:
                attempt += 1

                # 检查是否还在onboard页面
                current_url = self.driver.current_url
                if '/onboard' not in current_url:
                    self.log("debug", "已离开Onboard页面")
                    break

                # 查找Skip for now按钮
                skip_btn = self.driver.execute_script("""
                    const buttons = Array.from(document.querySelectorAll('button'));
                    return buttons.find(btn =>
                        btn.textContent.includes('Skip') && btn.textContent.includes('for now')
                    );
                """)

                if skip_btn:
                    self.log("info", "✅ 找到Skip for now按钮")
                    time.sleep(1)
                    skip_btn.click()
                    self.log("info", "🖱️ 已点击Skip for now按钮")
                    break

                if attempt % 20 == 0:
                    self.log("debug", f"等待Skip for now按钮... (attempt {attempt})")

            except Exception as e:
                if attempt % 40 == 0:
                    self.log("debug", f"监听Skip按钮中... {e}")

            time.sleep(0.5)

    def _handle_verification_failure(self):
        """处理验证失败 - 删除当前邮箱，获取下一个邮箱重新注册"""
        self.verification_failed = True
        self.update_status(RegisterStatus.FAILED, "验证失败，准备重试...")
        self._stop_monitoring = True

        self.log("warning", "⚠️ 验证失败，准备删除邮箱并重新注册...")

        # 删除当前邮箱
        if self.current_email_id:
            try:
                self.email_db.delete_email(self.current_email_id)
                self.log("info", f"✅ 已删除失败邮箱: {self.current_email} (ID: {self.current_email_id})")
            except Exception as e:
                self.log("warning", f"⚠️ 删除邮箱失败: {e}")

        # 等待2秒后重新开始
        time.sleep(2)

        try:
            # 获取下一个未使用的邮箱
            next_email_obj = self.email_db.get_unused_email()
            if not next_email_obj:
                self.log("error", "❌ 没有可用的邮箱了！")
                self.update_status(RegisterStatus.FAILED, "没有可用的邮箱")
                return

            next_email = next_email_obj.email
            self.log("info", f"🔄 获取下一个邮箱: {next_email}")

            # 重新调用start_register，完整走一遍流程
            self.start_register(next_email, {})

        except Exception as e:
            self.log("error", f"❌ 重新注册失败: {e}")
            self.update_status(RegisterStatus.FAILED, f"重新注册失败: {e}")

    def _monitor_captcha_complete(self):
        """监听人机验证完成并自动点击Continue"""
        self.log("info", "👀 开始监听人机验证完成...")
        self.update_status(RegisterStatus.WAITING_CAPTCHA, "等待人机验证...")
        attempt = 0

        while not self._stop_monitoring:
            try:
                attempt += 1

                captcha_input = self.driver.find_element(By.CSS_SELECTOR, 'input[name="captcha"]')

                if captcha_input and captcha_input.get_attribute('value'):
                    self.log("info", "✅ 人机验证完成！")
                    time.sleep(1)

                    continue_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"][name="action"]')

                    if continue_btn and not continue_btn.get_attribute('disabled'):
                        self.log("info", "🖱️ 自动点击Continue按钮...")
                        continue_btn.click()
                        self.log("info", "✅ Continue按钮已点击，等待页面跳转...")
                        self.update_status(RegisterStatus.EXTRACTING_INFO, "正在提交...")
                        break

            except NoSuchElementException:
                pass
            except Exception as e:
                if attempt % 20 == 0:
                    self.log("debug", f"等待人机验证中... (attempt {attempt})")

            time.sleep(0.5)

    def _monitor_verification_code(self):
        """监听验证码输入完成并自动点击Continue"""
        self.log("info", "👀 开始监听验证码输入...")
        attempt = 0
        max_attempts = 240  # 120秒超时（验证码页面用户需要手动输入，给更多时间）

        time.sleep(3)  # 等待3秒后再开始监听

        while not self._stop_monitoring and attempt < max_attempts:
            try:
                attempt += 1

                # 查找验证码输入框
                code_input = self.driver.find_element(By.CSS_SELECTOR, 'input#code[name="code"]')

                # 检查是否已输入验证码（长度大于4）
                if code_input and code_input.get_attribute('value') and len(code_input.get_attribute('value')) >= 4:
                    self.log("info", "✅ 检测到验证码已输入！")
                    time.sleep(1)

                    # 查找并点击Continue按钮
                    continue_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"][name="action"]')

                    if continue_btn and not continue_btn.get_attribute('disabled'):
                        self.log("info", "🖱️ 自动点击Continue按钮（验证码页面）...")
                        continue_btn.click()
                        self.log("info", "✅ Continue按钮已点击，等待验证结果...")
                        break
                else:
                    if attempt % 20 == 0:
                        self.log("debug", f"等待验证码输入中... (attempt {attempt})")

            except NoSuchElementException:
                # 验证码输入框不存在，可能还没跳转到验证码页面
                pass
            except Exception as e:
                if attempt % 20 == 0:
                    self.log("debug", f"监听验证码输入中... (attempt {attempt})")

            time.sleep(0.5)

        if attempt >= max_attempts:
            self.log("warning", "⚠️ 120秒内未检测到验证码输入，停止监听")

    def _monitor_skip_button(self):
        """监听Skip for now按钮并自动点击"""
        self.log("info", "👀 开始监听Skip for now按钮...")
        attempt = 0
        max_attempts = 120  # 60秒超时

        time.sleep(3)  # 等待3秒后再开始监听

        while not self._stop_monitoring and attempt < max_attempts:
            try:
                attempt += 1

                skip_btn = None

                # 策略1: 精确匹配
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                for btn in buttons:
                    if 'Skip for now' in btn.text:
                        skip_btn = btn
                        self.log("info", "✅ 找到Skip for now按钮（策略1）")
                        break

                # 策略2: 包含Skip
                if not skip_btn:
                    for btn in buttons:
                        if 'Skip' in btn.text and 'for now' in btn.text:
                            skip_btn = btn
                            self.log("info", "✅ 找到Skip for now按钮（策略2）")
                            break

                if skip_btn:
                    self.log("info", "🖱️ 自动点击Skip for now按钮...")
                    skip_btn.click()
                    self.log("info", "✅ Skip for now按钮已点击")
                    time.sleep(2)
                    break
                else:
                    if attempt % 10 == 0:
                        self.log("debug", f"等待Skip按钮中... (attempt {attempt})")

            except Exception as e:
                if attempt % 20 == 0:
                    self.log("debug", f"监听Skip按钮中... (attempt {attempt})")

            time.sleep(0.5)

        if attempt >= max_attempts:
            self.log("warning", "⚠️ 60秒内未检测到Skip按钮，停止监听")

    def _monitor_auth_continue_page(self):
        """监听auth/continue页面并自动提取信息"""
        self.log("info", "👀 开始监听auth/continue页面...")
        attempt = 0
        max_attempts = 200  # 100秒超时

        time.sleep(5)  # 等待5秒后再开始监听

        while not self._stop_monitoring and attempt < max_attempts:
            try:
                attempt += 1

                current_url = self.driver.current_url

                # 检查是否到达auth/continue或complete-signup页面
                if '/auth/continue' in current_url or '/complete-signup' in current_url:
                    self.log("info", f"✅ 检测到目标页面: {current_url}")
                    time.sleep(2)

                    # 自动提取账号信息
                    self.log("info", "🔍 开始提取账号信息...")
                    result = self.extract_account_info()

                    if result:
                        self.log("info", "✅ 账号信息提取成功！")
                        self.update_status(RegisterStatus.SUCCESS, "注册成功")
                    else:
                        self.log("error", "❌ 账号信息提取失败")
                        self.update_status(RegisterStatus.FAILED, "提取信息失败")

                    self._stop_monitoring = True
                    break
                else:
                    if attempt % 20 == 0:
                        self.log("debug", f"等待auth/continue页面中... 当前URL: {current_url[:50]}...")

            except Exception as e:
                if attempt % 20 == 0:
                    self.log("debug", f"监听auth/continue页面中... (attempt {attempt})")

            time.sleep(0.5)

        if attempt >= max_attempts:
            self.log("warning", "⚠️ 100秒内未检测到auth/continue页面，停止监听")

    def extract_account_info(self) -> Optional[Dict[str, Any]]:
        """提取账号信息"""
        try:
            current_url = self.driver.current_url
            self.log("info", f"📄 当前页面: {current_url}")

            # 提取tenant_url
            tenant_url = None
            if '/auth/continue' in current_url:
                tenant_url = current_url.split('/auth/continue')[0]
            elif '/complete-signup' in current_url:
                tenant_url = current_url.split('/complete-signup')[0]

            if not tenant_url:
                self.log("error", "❌ 无法提取tenant_url")
                return None

            self.log("info", f"✅ 提取到tenant_url: {tenant_url}")

            # 提取auth session
            auth_session = None
            try:
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    if cookie['name'] == 'auth0':
                        auth_session = cookie['value']
                        break

                if auth_session:
                    self.log("info", f"✅ 提取到auth_session: {auth_session[:20]}...")
                else:
                    self.log("warning", "⚠️ 未找到auth_session cookie")
            except Exception as e:
                self.log("warning", f"⚠️ 提取auth_session失败: {e}")

            # 保存到数据库
            account = {
                'email': self.current_email,
                'tenant_url': tenant_url,
                'auth_session': auth_session,
                'status': 'active',
                'card_bound': False
            }

            account_id = self.db.add_account(
                email=self.current_email,
                tenant_url=tenant_url,
                auth_session=auth_session
            )

            if account_id:
                self.current_account_id = account_id
                self.log("info", f"✅ 账号信息已保存到数据库 (ID: {account_id})")

                # 添加日志
                self.db.add_log(
                    account_id=account_id,
                    action='register',
                    status='success',
                    message=f'注册成功: {self.current_email}'
                )

                return account
            else:
                self.log("error", "❌ 保存账号信息到数据库失败")
                return None

        except Exception as e:
            self.log("error", f"❌ 提取账号信息失败: {e}")
            return None

    def bind_card(self, card_info: Dict[str, Any], user_info: Dict[str, Any]) -> bool:
        """绑定卡片（待实现）"""
        self.log("warning", "⚠️ 绑卡功能待实现")
        return False
