# -*- coding: utf-8 -*-
"""
Outlook 邮箱自动注册模块
"""
import time
import random
import string
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from config.settings import Settings
from utils.logger import get_logger
from utils.file_manager import FileManager
from core.proxy import create_stealth_browser

logger = get_logger(__name__)


class OutlookRegistration:
    """Outlook 邮箱自动注册类"""

    def __init__(self, progress_callback=None, confirm_callback=None, confirm_success_callback=None):
        """
        初始化浏览器（使用 undetected-chromedriver 绕过反检测）

        Args:
            progress_callback: 进度回调函数，用于UI更新
            confirm_callback: 确认回调函数，用于需要用户确认的操作（如验证码完成）
            confirm_success_callback: 确认注册成功回调函数，返回True表示成功，False表示失败
        """
        self.progress_callback = progress_callback
        self.confirm_callback = confirm_callback
        self.confirm_success_callback = confirm_success_callback
        self.driver = None
        self.wait = None
        self.user_info = {}  # 存储用户信息

        # 初始化浏览器
        self._init_browser()

    def _init_browser(self):
        """初始化浏览器 - 使用完整的指纹伪装配置"""
        self._update_progress("正在启动浏览器...")

        try:
            self._update_progress("将自动检测Chrome版本并管理chromedriver")

            # 使用公共的浏览器指纹伪装函数
            self.driver = create_stealth_browser(
                chrome_version=Settings.CHROME_VERSION,
                headless=False
            )
            self._update_progress("浏览器启动成功")
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            raise Exception(f"浏览器启动失败: {e}")

        self.wait = WebDriverWait(self.driver, Settings.DEFAULT_TIMEOUT)

    def _update_progress(self, message):
        """更新进度信息"""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)



    def generate_random_string(self, length=8):
        """生成随机字符串"""
        letters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(letters) for i in range(length))

    def generate_password(self):
        """生成符合 Outlook 要求的强密码（含大小写、数字、特殊字符）"""
        upper = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        lower = random.choice("abcdefghijklmnopqrstuvwxyz")
        digit = random.choice("0123456789")
        special = random.choice("!@#$%^&*")

        rest_length = 8 - 4
        all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        remaining = ''.join(random.choices(all_chars, k=rest_length))

        password_list = [upper, lower, digit, special] + list(remaining)
        random.shuffle(password_list)
        return ''.join(password_list)

    def generate_random_chinese_name(self):
        """生成随机繁体中文姓名"""
        # 常见繁体中文姓氏
        last_names = [
            '陳', '林', '黃', '張', '李', '王', '吳', '劉', '蔡', '楊',
            '許', '鄭', '謝', '郭', '洪', '曾', '邱', '廖', '賴', '周',
            '徐', '蘇', '葉', '莊', '呂', '江', '何', '蕭', '羅', '高',
            '潘', '簡', '朱', '鍾', '彭', '游', '詹', '胡', '施', '沈'
        ]

        # 常見繁體中文名字用字
        first_name_chars = [
            '志', '明', '偉', '傑', '華', '強', '軍', '平', '剛', '勇',
            '磊', '超', '輝', '鵬', '濤', '浩', '亮', '政', '謙', '宇',
            '文', '斌', '英', '梅', '芳', '娜', '敏', '靜', '麗', '強',
            '婷', '穎', '秀', '珍', '霞', '香', '月', '鳳', '美', '琳',
            '素', '雲', '蓮', '真', '環', '雪', '榮', '愛', '妹', '蘭',
            '曉', '東', '建', '國', '軍', '新', '利', '清', '飛', '彬'
        ]

        last_name = random.choice(last_names)
        # 名字1-2個字
        name_length = random.randint(1, 2)
        first_name = ''.join(random.choice(first_name_chars) for _ in range(name_length))

        return last_name, first_name

    def generate_user_info(self):
        """生成完整用户信息（邮箱 + 密码 + 生日 + 姓名）"""
        # 生成无规律的邮箱前缀：字母开头 + 字母数字混合（6-10位）
        length = random.randint(6, 10)
        first_char = random.choice(string.ascii_lowercase)
        rest_chars = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length - 1))
        username = first_char + rest_chars
        email = f"{username}@outlook.com"

        # 随机生成密码
        password = self.generate_password()

        # 随机生成生日
        year = random.randint(1990, 2015)
        month = random.randint(1, 12)
        day = random.randint(1, 28)

        # 随机生成繁体中文姓名
        last_name, first_name = self.generate_random_chinese_name()

        return {
            'email': email,
            'username': username,
            'password': password,
            'birth_year': str(year),
            'birth_month': str(month),
            'birth_day': str(day),
            'last_name': last_name,
            'first_name': first_name
        }

    def save_account_info(self, user_info, status="未注册"):
        """保存账号信息到文件"""
        return FileManager.save_account(user_info, status)

    def update_account_status(self, email, new_status="已注册"):
        """更新账号状态"""
        return FileManager.update_account_status(email, new_status)

    def safe_send_keys(self, locators, text, retry=2, timeout=5):
        """带重试的安全输入，支持多种定位方式（快速超时版本）"""
        # 如果传入的是单个定位器（元组），转换为列表
        if isinstance(locators, tuple):
            locators = [locators]

        for locator in locators:
            for i in range(retry):
                try:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable(locator)
                    )
                    element.click()
                    element.clear()
                    element.send_keys(text)
                    print(f"✅ 成功使用定位器: {locator}")
                    return True
                except StaleElementReferenceException:
                    print(f"🔁 元素过期，第 {i+1} 次重试...")
                    time.sleep(0.5)
                    continue
                except Exception as e:
                    # 只打印简短错误信息，不打印整个堆栈
                    print(f"⚠️ 定位器 {locator} 失败，尝试下一个...")
                    break

        print(f"❌ 所有定位器均失败，共尝试 {len(locators)} 种方式")
        return False

    def smart_find(self, locators, timeout=5):
        """尝试多种定位方式，返回第一个成功元素（快速超时版本）"""
        # 如果传入的是单个定位器（元组），转换为列表
        if isinstance(locators, tuple):
            locators = [locators]

        for locator in locators:
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located(locator)
                )
                print(f"✅ 成功定位元素: {locator}")
                return element
            except TimeoutException:
                print(f"⚠️ 定位器超时: {locator}")
                continue
        raise TimeoutException(f"❌ 所有定位方式均失败，共尝试 {len(locators)} 种")

    def smart_click(self, locators, retry=2, timeout=5):
        """智能点击按钮，支持多种定位方式和重试（快速超时版本）"""
        # 如果传入的是单个定位器（元组），转换为列表
        if isinstance(locators, tuple):
            locators = [locators]

        for locator in locators:
            for i in range(retry):
                try:
                    btn = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable(locator)
                    )
                    # 尝试滚动到元素
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.3)
                    btn.click()
                    print(f"✅ 成功点击: {locator}")
                    return True
                except StaleElementReferenceException:
                    print(f"🔁 元素过期，第 {i+1} 次重试...")
                    time.sleep(0.5)
                    continue
                except Exception as e:
                    print(f"⚠️ 定位器 {locator} 失败: {str(e)[:100]}")
                    break

        print(f"❌ 所有点击尝试均失败，共尝试 {len(locators)} 种定位器")
        return False

    def _dump_dropdown_failure(self, button_elem, field_name: str, value):
        """下拉选择失败时的诊断 dump：截图 + DOM 关键元素 outerHTML + 当前 URL。

        输出位置：
            - 截图：data/debug_screenshots/dropdown_fail_{field_name}_{timestamp}.png
            - DOM/属性信息：直接 print 到日志面板

        参数:
            button_elem: 触发下拉的按钮 WebElement（用于读 aria-expanded / outerHTML）
            field_name: 字段名（"日期"/"月份"/...），用于截图命名和日志标识
            value: 期望选中的值（"28"/"July"/...）
        """
        from pathlib import Path
        from datetime import datetime

        try:
            print("=" * 70)
            print(f"🔧 [DOM DUMP] 下拉选择失败：{field_name}=「{value}」，输出诊断信息")
            print("=" * 70)

            # ---- 1. 截图 ----
            try:
                debug_dir = Path("data/debug_screenshots")
                debug_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 字段名可能含中文，用 ascii 安全名
                safe_field = "".join(c if c.isalnum() else "_" for c in field_name)
                screenshot_path = debug_dir / f"dropdown_fail_{safe_field}_{ts}.png"
                self.driver.save_screenshot(str(screenshot_path))
                print(f"📸 截图已保存: {screenshot_path.resolve()}")
            except Exception as e:
                print(f"⚠️ 截图失败: {e}")

            # ---- 2. 当前 URL ----
            try:
                print(f"🌐 当前URL: {self.driver.current_url}")
            except Exception as e:
                print(f"⚠️ 读 URL 失败: {e}")

            # ---- 3. 触发按钮的状态 ----
            if button_elem is not None:
                try:
                    aria_expanded = button_elem.get_attribute("aria-expanded")
                    aria_haspopup = button_elem.get_attribute("aria-haspopup")
                    btn_html = self.driver.execute_script(
                        "return arguments[0].outerHTML;", button_elem
                    )
                    snippet = (btn_html or "")[:400]
                    print(f"🔘 触发按钮: aria-expanded={aria_expanded!r}, aria-haspopup={aria_haspopup!r}")
                    print(f"   outerHTML[:400]={snippet}")
                except Exception as e:
                    print(f"⚠️ 读按钮属性失败: {e}")

            # ---- 4. 所有 [role=option] 元素的 text ----
            try:
                options = self.driver.find_elements(By.XPATH, "//*[@role='option']")
                print(f"🔎 [role=option] 元素共 {len(options)} 个")
                for i, opt in enumerate(options[:40]):
                    try:
                        text = (opt.text or "").strip()
                        opt_html = self.driver.execute_script(
                            "return arguments[0].outerHTML;", opt
                        )
                        print(f"   [{i:02d}] text={text!r}  html[:160]={(opt_html or '')[:160]}")
                    except Exception:
                        pass
                if len(options) > 40:
                    print(f"   ... 省略 {len(options) - 40} 个")
            except Exception as e:
                print(f"⚠️ 抓 [role=option] 失败: {e}")

            # ---- 5. 原生 <select> 与 <option> ----
            try:
                selects = self.driver.find_elements(By.TAG_NAME, "select")
                print(f"📜 原生 <select> 元素共 {len(selects)} 个")
                for i, sel in enumerate(selects):
                    try:
                        sel_name = sel.get_attribute("name") or sel.get_attribute("id") or "?"
                        opts = sel.find_elements(By.TAG_NAME, "option")
                        sample = [(o.get_attribute("value"), (o.text or "").strip()) for o in opts[:35]]
                        print(f"   <select #{i} name/id={sel_name}> 共 {len(opts)} 个 <option>，前35个: {sample}")
                    except Exception:
                        pass
            except Exception as e:
                print(f"⚠️ 抓 <select> 失败: {e}")

            # ---- 6. [role=listbox] 容器 ----
            try:
                lboxes = self.driver.find_elements(By.XPATH, "//*[@role='listbox']")
                print(f"📦 [role=listbox] 元素共 {len(lboxes)} 个")
                for i, lb in enumerate(lboxes[:5]):
                    try:
                        lb_html = self.driver.execute_script(
                            "return arguments[0].outerHTML;", lb
                        )
                        print(f"   [{i}] outerHTML[:600]={(lb_html or '')[:600]}")
                    except Exception:
                        pass
            except Exception as e:
                print(f"⚠️ 抓 [role=listbox] 失败: {e}")

            # ---- 7. 提示用户怎么办 ----
            print("=" * 70)
            print(f"💡 把以上日志（特别是 [role=option] 的 text 和 <select> 列表）+ 截图发给开发者")
            print(f"   即可精准修复 {field_name} 下拉的 selector。")
            print("=" * 70)

        except Exception as outer_e:
            print(f"⚠️ DOM dump 自身出错: {outer_e}")

    def smart_select_dropdown(self, button_locators, value, field_name="选项"):
        """智能选择下拉菜单（支持多种选择方式和多语言）"""
        btn = None
        try:
            # 1. 找到并点击下拉按钮
            btn = self.smart_find(button_locators)

            # 滚动到元素
            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.3)

            # 使用JavaScript点击，避免被其他元素遮挡
            try:
                btn.click()
            except Exception as e:
                print(f"⚠️ Selenium点击失败，尝试JavaScript点击")
                self.driver.execute_script("arguments[0].click();", btn)

            print(f"📋 打开{field_name}下拉菜单")
            time.sleep(1)  # 等待下拉菜单展开

            # 2. 尝试多种方式选择选项
            selected = False

            # 方式1：精确匹配文本
            if not selected:
                try:
                    option = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, f"//div[@role='option' and text()='{value}']"))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", option)
                    time.sleep(0.2)
                    option.click()
                    selected = True
                    print(f"✅ {field_name}选择成功: {value}")
                except:
                    pass

            # 方式2：包含文本
            if not selected:
                try:
                    option = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, f"//div[@role='option' and contains(text(), '{value}')]"))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", option)
                    time.sleep(0.2)
                    option.click()
                    selected = True
                    print(f"✅ {field_name}选择成功: {value}")
                except:
                    pass

            # 方式3：遍历所有选项（支持多语言）
            if not selected:
                try:
                    options = self.driver.find_elements(By.XPATH, "//div[@role='option']")
                    for option in options:
                        option_text = option.text.strip()
                        # 支持多种匹配方式
                        if (option_text == str(value) or
                            str(value) in option_text or
                            option_text in str(value)):
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", option)
                            time.sleep(0.2)
                            option.click()
                            selected = True
                            print(f"✅ {field_name}选择成功: {value}")
                            break
                except Exception as e:
                    pass

            if not selected:
                # 三种 fallback 都失败 → dump 当前 DOM/截图，方便诊断
                self._dump_dropdown_failure(btn, field_name, value)
                raise Exception(f"❌ 无法选择{field_name}: {value}")

            time.sleep(0.5)
            return True

        except Exception as e:
            print(f"❌ {field_name}选择失败: {e}")
            return False

    def handle_perimeterx_captcha(self):
        """处理 PerimeterX 人机验证（智能检测 + 自动/手动混合）"""
        try:
            self._update_progress("\n" + "=" * 70)
            self._update_progress("🤖 检测 PerimeterX 人机验证...")
            self._update_progress("=" * 70)

            # 检测是否出现验证码页面（支持中文和英文）
            try:
                captcha_title = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), '证明你不是机器人') or contains(text(), 'Prove you')]"))
                )
                self._update_progress("⚠️  检测到 PerimeterX 验证码！")
            except:
                self._update_progress("✅ 未检测到验证码，继续...")
                return True

            # 尝试自动处理
            self._update_progress("🔄 尝试自动处理验证码...")

            try:
                # 查找 iframe
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[title='验证质询']"))
                )
                print("✅ 找到验证 iframe")

                # 切换到 iframe
                self.driver.switch_to.frame(iframe)
                print("✅ 切换到 iframe")

                # 随机等待（模拟人类）
                wait_time = random.uniform(1.5, 3)
                print(f"⏳ 随机等待 {wait_time:.1f} 秒（模拟人类行为）...")
                time.sleep(wait_time)

                # 查找按钮（可能是 button 或 div）
                button = None
                try:
                    button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button"))
                    )
                    print("✅ 找到验证按钮（button）")
                except:
                    try:
                        button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='button']"))
                        )
                        print("✅ 找到验证按钮（div[role='button']）")
                    except:
                        print("❌ 未找到验证按钮")

                if button:
                    # 使用 ActionChains 模拟长按
                    print("🖱️  模拟长按按钮...")
                    actions = ActionChains(self.driver)

                    # 移动到按钮
                    actions.move_to_element(button)
                    actions.pause(random.uniform(0.3, 0.8))

                    # 长按 3-5 秒
                    press_duration = random.uniform(3, 5)
                    print(f"⏱️  长按 {press_duration:.1f} 秒...")
                    actions.click_and_hold(button)
                    actions.pause(press_duration)
                    actions.release(button)

                    # 执行操作
                    actions.perform()
                    print("✅ 长按操作完成")

                    # 切回主页面
                    self.driver.switch_to.default_content()

                    # 等待验证结果
                    time.sleep(3)

                    # 检查是否通过（支持中文和英文）
                    try:
                        still_captcha = self.driver.find_element(By.XPATH, "//h1[contains(text(), '证明你不是机器人') or contains(text(), 'Prove you')]")
                        print("⚠️ 自动处理失败，验证码仍然存在")
                        return False
                    except:
                        print("✅ 验证码已通过！")
                        return True
                else:
                    self.driver.switch_to.default_content()
                    return False

            except Exception as e:
                print(f"❌ 自动处理失败: {e}")
                self.driver.switch_to.default_content()
                return False

        except Exception as e:
            print(f"❌ 验证码处理异常: {e}")
            return False

    # ⚠️ 注释掉 iframe 切换逻辑 —— 当前页面没有 iframe，切换会导致后续定位失败
    # def switch_to_main_iframe(self):
    #     self.driver.switch_to.default_content()
    #     try:
    #         iframe = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
    #         self.driver.switch_to.frame(iframe)
    #         print("✅ 已切换到 iframe")
    #     except TimeoutException:
    #         print("ℹ️ 未检测到 iframe，使用主页面")

    def register(self):
        """执行注册流程"""
        try:
            self._update_progress("正在访问 Outlook 注册页面...")
            self.driver.get("https://signup.live.com/")

            # 等待页面完全加载
            self._update_progress("等待页面加载...")
            time.sleep(5)

            # 打印当前页面标题，确认页面加载成功
            logger.info(f"当前页面: {self.driver.title}")

            # === 0. 处理首页同意按钮（个人数据导出许可）===
            print("🔍 检查是否有首页同意按钮...")
            try:
                # 检测页面语言（中文还是英文）
                page_source = self.driver.page_source
                is_english = "Accept" in page_source or "Agree" in page_source or "Next" in page_source

                if is_english:
                    print("ℹ️  检测到英文环境，跳过同意页面")
                else:
                    # 中文环境才需要点击同意按钮
                    consent_btn_locators = [
                        (By.ID, "nextButton"),
                        (By.CSS_SELECTOR, "button[data-testid='primaryButton']"),
                        (By.XPATH, "//button[contains(text(), '同意并继续')]"),  # 中文
                    ]

                    # 尝试点击同意按钮
                    if self.smart_click(consent_btn_locators):
                        print("✅ 已点击【同意并继续】按钮")
                        time.sleep(3)
                    else:
                        print("ℹ️  未检测到首页同意按钮，继续流程")
            except Exception as e:
                print(f"ℹ️  首页同意按钮处理跳过: {e}")

            # 生成用户信息
            user_info = self.generate_user_info()
            self.user_info = user_info  # 保存到实例变量
            print(f"📧 生成邮箱: {user_info['email']}")
            print(f"🔑 生成密码: {user_info['password']}")
            self._update_progress(f"📧 生成邮箱: {user_info['email']}")
            self._update_progress(f"🔑 生成密码: {user_info['password']}")

            # === 1. 输入邮箱 ===
            print("📝 正在定位邮箱输入框...")

            # ✅ 支持中文和英文环境
            email_locators = [
                (By.CSS_SELECTOR, "input[type='email'][name='电子邮件']"),  # 中文
                (By.CSS_SELECTOR, "input[type='email']"),                   # 通用
                (By.XPATH, "//input[@type='email']"),                       # 兜底
                (By.NAME, "loginfmt"),                                      # 英文环境备选
            ]

            # 使用增强版 safe_send_keys
            if not self.safe_send_keys(email_locators, user_info['email']):
                raise Exception("❌ 无法输入邮箱地址")

            print("✅ 邮箱输入成功")

            # 点击下一步（支持中文和英文）
            next_btn_locators = [
                (By.XPATH, "//button[text()='下一步']"),                    # 中文
                (By.XPATH, "//button[contains(text(), 'Next')]"),           # 英文
                (By.CSS_SELECTOR, "button[data-testid='primaryButton']"),   # 通用
                (By.XPATH, "//button[@type='submit']"),                     # 兜底
            ]
            if not self.smart_click(next_btn_locators):
                raise Exception("❌ 无法点击【下一步】")

            time.sleep(3)

            # === 2. 输入密码 ===
            print("🔒 输入密码...")

            pwd_locators = [
                (By.XPATH, "//input[@type='password' and @placeholder]"),  # ✅ 实测有效
                (By.XPATH, "//input[@type='password']"),  # ✅ 兜底
            ]
            if not self.safe_send_keys(pwd_locators, user_info['password']):
                raise Exception("❌ 无法输入密码")

            print("✅ 密码输入成功")

            # 💾 立即保存账号信息（未注册状态）
            print("\n💾 保存账号信息（未注册状态）...")
            self._update_progress("💾 保存账号信息（未注册状态）...")
            if FileManager.save_account(user_info, status="未注册"):
                print("✅ 账号信息已保存")
                print(f"   📬 邮箱: {user_info['email']}")
                print(f"   🔑 密码: {user_info['password']}")
                print(f"   📝 状态: 未注册")
                self._update_progress("✅ 账号信息已保存（未注册状态）")
            else:
                print("⚠️ 账号信息保存失败，但继续注册流程")
                self._update_progress("⚠️ 账号信息保存失败")

            # 点击下一步（支持中文和英文）
            next_btn_locators = [
                (By.XPATH, "//button[text()='下一步']"),                    # 中文
                (By.XPATH, "//button[contains(text(), 'Next')]"),           # 英文
                (By.CSS_SELECTOR, "button[data-testid='primaryButton']"),   # 通用
            ]
            if not self.smart_click(next_btn_locators):
                raise Exception("❌ 无法点击密码页【下一步】")

            time.sleep(3)

            # === 4. 生日 ===
            print("🎂 输入生日...")

            try:
                # 根据最新DOM，这些是下拉按钮，不是select元素
                year_locators = [(By.NAME, "BirthYear"), (By.ID, "floatingLabelInput23")]
                month_locators = [(By.NAME, "BirthMonth"), (By.ID, "BirthMonthDropdown")]
                day_locators = [(By.NAME, "BirthDay"), (By.ID, "BirthDayDropdown")]

                # 输入年份（这是个input框）
                year_input = self.smart_find(year_locators)
                year_input.click()
                year_input.clear()
                year_input.send_keys(user_info['birth_year'])
                print(f"✅ 年份输入: {user_info['birth_year']}")
                time.sleep(0.5)

                # 选择月份（支持中文和英文）
                month_num = user_info['birth_month']
                month_names_en = ['January', 'February', 'March', 'April', 'May', 'June',
                                 'July', 'August', 'September', 'October', 'November', 'December']

                # 尝试多种月份格式
                month_attempts = [
                    month_names_en[int(month_num)-1] if 1 <= int(month_num) <= 12 else None,  # 英文：February
                    f"{month_num}月",  # 中文格式：2月
                    str(month_num),     # 纯数字：2
                ]

                month_selected = False
                for month_val in month_attempts:
                    if month_val and self.smart_select_dropdown(month_locators, month_val, "月份"):
                        month_selected = True
                        break

                if not month_selected:
                    raise Exception(f"❌ 无法选择月份: {month_num}，尝试过: {month_attempts}")

                # 选择日期（使用智能下拉选择）
                if not self.smart_select_dropdown(day_locators, user_info['birth_day'], "日期"):
                    raise Exception(f"❌ 无法选择日期: {user_info['birth_day']}")

                time.sleep(1)

                # 点击下一步（支持中文和英文）
                next_btn_locators = [
                    (By.XPATH, "//button[text()='下一步']"),                    # 中文
                    (By.XPATH, "//button[contains(text(), 'Next')]"),           # 英文
                    (By.CSS_SELECTOR, "button[data-testid='primaryButton']"),   # 通用
                    (By.XPATH, "//button[@type='submit']"),                     # 兜底
                ]
                if not self.smart_click(next_btn_locators):
                    raise Exception("❌ 无法点击生日页【下一步】")

                print("✅ 生日信息提交成功")
                time.sleep(3)

            except Exception as e:
                print(f"⚠️ 生日输入失败: {e}")
                # 不关闭浏览器，让用户可以看到当前状态
                print("\n" + "="*70)
                print("🔍 浏览器保持打开，你可以检查当前页面的DOM结构")
                print("="*70)
                raise

            # === 5. 输入姓名 ===
            print("👨 输入姓名...")

            try:
                # 根据最新DOM结构
                last_name_locators = [
                    (By.ID, "lastNameInput"),  # ✅ 最精准
                    (By.NAME, "lastNameInput"),  # ✅ 兜底
                ]
                first_name_locators = [
                    (By.ID, "firstNameInput"),  # ✅ 最精准
                    (By.NAME, "firstNameInput"),  # ✅ 兜底
                ]

                # 输入姓氏（使用生成的繁体中文姓氏）
                last_name = user_info.get('last_name', '陳')
                if not self.safe_send_keys(last_name_locators, last_name):
                    print(f"⚠️ 姓氏输入失败，尝试继续...")
                else:
                    print(f"✅ 姓氏输入成功: {last_name}")

                time.sleep(0.5)

                # 输入名字（使用生成的繁体中文名字）
                first_name = user_info.get('first_name', '志明')
                if not self.safe_send_keys(first_name_locators, first_name):
                    print(f"⚠️ 名字输入失败，尝试继续...")
                else:
                    print(f"✅ 名字输入成功: {first_name}")

                time.sleep(1)

                # 点击下一步（支持中文和英文）
                next_btn_locators = [
                    (By.XPATH, "//button[text()='下一步']"),                    # 中文
                    (By.XPATH, "//button[contains(text(), 'Next')]"),           # 英文
                    (By.CSS_SELECTOR, "button[data-testid='primaryButton']"),   # 通用
                    (By.XPATH, "//button[@type='submit']"),                     # 兜底
                ]
                if not self.smart_click(next_btn_locators):
                    print("⚠️ 无法点击姓名页【下一步】，尝试继续...")
                else:
                    print("✅ 姓名信息提交成功")

                time.sleep(3)

            except Exception as e:
                print(f"⚠️ 姓名输入失败: {e}")
                print("ℹ️  尝试继续后续流程...")

            # === 7. 验证码（智能处理）===

            print("\n📋 当前账号信息:")
            print(f"   📬 邮箱: {user_info['email']}")
            print(f"   🔑 密码: {user_info['password']}")
            print(f"   🎂 生日: {user_info['birth_year']}-{user_info['birth_month']}-{user_info['birth_day']}")
            print()

            # 尝试自动处理验证码
            captcha_passed = self.handle_perimeterx_captcha()

            if not captcha_passed:
                # 自动处理失败，转为手动
                self._update_progress("\n" + "=" * 70)
                self._update_progress("⚠️  自动处理失败，需要手动操作")
                self._update_progress("=" * 70)
                self._update_progress("\n🛑 请在浏览器中完成以下操作:")
                self._update_progress("   1. 完成验证码验证（长按按钮或其他方式）")
                self._update_progress("   2. 如果有其他步骤，请继续完成")
                self._update_progress("   3. 看到注册成功页面后，点击确认按钮")
                self._update_progress("\n⏰ 浏览器将保持打开状态，等待你的操作...")
                self._update_progress("=" * 70)

                # 等待用户确认（通过UI对话框或控制台输入）
                if self.confirm_callback:
                    # 使用UI回调
                    self.confirm_callback("请在浏览器中完成验证码，完成后点击确定继续")
                else:
                    # 降级到控制台输入
                    input("\n👉 完成验证码后，按 Enter 键继续...")

            # === 8. 确认注册状态 ===
            print("\n🔍 正在检查注册状态...")
            time.sleep(2)

            # 检查浏览器窗口是否还在
            try:
                # 尝试获取当前 URL
                current_url = self.driver.current_url
                print(f"📍 当前页面: {current_url}")

                # 检查是否有成功标志
                success_indicators = [
                    "//h1[contains(text(), '欢迎')]",
                    "//h1[contains(text(), 'Welcome')]",
                    "//div[contains(text(), '成功')]",
                    "//div[contains(text(), 'success')]",
                    "//h1[contains(text(), 'Microsoft')]",  # Microsoft 账户说明页面
                    "//button[contains(text(), '确定')]",  # 确定按钮
                ]

                for indicator in success_indicators:
                    try:
                        element = self.driver.find_element(By.XPATH, indicator)
                        if element:
                            print("✅ 检测到注册成功标志！")
                            break
                    except:
                        continue

            except Exception as e:
                print(f"⚠️ 无法访问浏览器窗口: {e}")
                print("💡 这通常意味着页面已跳转或窗口已关闭")

            # 自动检测注册是否成功
            print("\n" + "=" * 70)
            print("📋 正在检测注册结果...")
            print("=" * 70)

            # 等待一下让页面稳定
            time.sleep(5)

            # 检测成功标志
            registration_success = False
            try:
                # 检查URL是否包含成功标志
                current_url = self.driver.current_url
                print(f"当前URL: {current_url}")

                # 成功的URL特征
                success_url_patterns = [
                    'account.microsoft.com',
                    'signup.live.com/proofs',  # 验证页面也算成功
                    'account.live.com',
                ]

                for pattern in success_url_patterns:
                    if pattern in current_url:
                        print(f"✅ URL包含成功标志: {pattern}")
                        registration_success = True
                        break

                # 如果URL检测不出来，检查页面元素（支持中文和英文）
                if not registration_success:
                    success_elements = [
                        "//h1[contains(text(), 'Microsoft')]",
                        "//div[contains(text(), '欢迎')]",
                        "//div[contains(text(), 'Welcome')]",
                        "//button[contains(text(), '确定')]",
                        "//button[contains(text(), 'OK')]",
                        "//div[contains(@class, 'success')]",
                    ]

                    for xpath in success_elements:
                        try:
                            element = self.driver.find_element(By.XPATH, xpath)
                            if element:
                                print(f"✅ 检测到成功元素: {xpath}")
                                registration_success = True
                                break
                        except:
                            continue

            except Exception as e:
                print(f"⚠️ 检测异常: {e}")

            # === 9. 让用户手动确认注册结果 ===
            # 🔥 关键修改：不管自动检测结果如何，都让用户手动确认
            print("\n" + "=" * 70)
            print("⏸️  浏览器保持打开，请手动确认注册结果")
            print("=" * 70)

            if registration_success:
                print("✅ 自动检测：注册可能成功")
                self._update_progress("✅ 自动检测：注册可能成功")
            else:
                print("⚠️  自动检测：未能确认注册成功")
                self._update_progress("⚠️  自动检测：未能确认注册成功")

            print("\n📋 当前账号信息:")
            print(f"   📬 邮箱: {user_info['email']}")
            print(f"   🔑 密码: {user_info['password']}")
            print(f"   🎂 生日: {user_info['birth_year']}-{user_info['birth_month']}-{user_info['birth_day']}")
            print()

            self._update_progress("\n" + "=" * 70)
            self._update_progress("⏸️  请在浏览器中检查注册结果")
            self._update_progress("=" * 70)
            self._update_progress(f"📬 邮箱: {user_info['email']}")
            self._update_progress(f"🔑 密码: {user_info['password']}")
            self._update_progress("\n⏳ 等待你在UI中确认注册是否成功...")

            # 🔥 关键：使用confirm_success_callback让用户手动确认注册是否成功
            # 这会弹出UI对话框，让用户选择"成功"或"失败"
            if self.confirm_success_callback:
                # 调用回调函数，返回True表示成功，False表示失败
                final_success = self.confirm_success_callback(
                    f"请在浏览器中检查注册是否成功\n\n"
                    f"📬 邮箱: {user_info['email']}\n"
                    f"🔑 密码: {user_info['password']}\n\n"
                    f"如果注册成功，点击【是】\n"
                    f"如果注册失败，点击【否】"
                )
            else:
                # 降级到控制台输入
                user_confirm = input("\n👉 注册是否成功？(y/n): ").strip().lower()
                final_success = (user_confirm == 'y')

            if final_success:
                # 更新账号状态为已注册
                print(f"\n✅ 用户确认注册成功！正在更新账号状态...")
                self._update_progress("✅ 用户确认注册成功！")

                try:
                    email = str(user_info.get('email', ''))

                    # 更新账号状态
                    if FileManager.update_account_status(email, new_status="已注册"):
                        print("✅ 账号状态已更新为：已注册")
                        self._update_progress(f"✅ 账号状态已更新为：已注册")
                    else:
                        print("⚠️ 更新状态失败，但账号信息已在之前保存")
                        self._update_progress("⚠️ 更新状态失败")

                    # 打印账号信息
                    print("\n" + "=" * 70)
                    print("📋 最终账号信息：")
                    print(f"   📬 邮箱: {email}")
                    print(f"   🔑 密码: {user_info.get('password', '')}")
                    print(f"   🎂 生日: {user_info.get('birth_year', '')}-{user_info.get('birth_month', '')}-{user_info.get('birth_day', '')}")
                    print(f"   ✅ 状态: 已注册")
                    print("=" * 70)

                    self._update_progress("="*60)
                    self._update_progress("📋 注册成功！")
                    self._update_progress(f"📬 邮箱: {email}")
                    self._update_progress(f"🔑 密码: {user_info.get('password', '')}")
                    self._update_progress(f"✅ 状态: 已注册")
                    self._update_progress("="*60)

                except Exception as e:
                    print(f"⚠️ 保存账号信息失败: {e}")
                    self._update_progress(f"⚠️ 保存失败: {e}")

                # 保存user_info到实例变量，供外部访问
                self.user_info = user_info
                return True
            else:
                print("\n⚠️ 用户确认注册失败")
                print("   账号信息已保存为'未注册'状态")
                self._update_progress("⚠️ 用户确认注册失败")

                # 保存user_info
                self.user_info = user_info
                return False

        except Exception as e:
            print(f"❌ 注册失败: {str(e)}")
            self._update_progress(f"❌ 注册失败: {str(e)}")

            # 错误时保持浏览器打开，让用户可以检查DOM
            print("\n" + "="*70)
            print("🔍 浏览器保持打开状态，你可以：")
            print("   1. 打开浏览器开发者工具（F12）检查当前页面DOM")
            print("   2. 查看元素的ID、Name、XPath等属性")
            print("   3. 将这些信息提供给开发者以更新定位器")
            print("   4. 手动完成操作后，关闭浏览器")
            print("="*70)

            self.user_info = {}
            return False

    def close(self, force=False):
        """关闭浏览器"""
        if not force:
            print("\n👋 准备关闭浏览器...")
            time.sleep(1)
        try:
            # 检查浏览器是否还在运行
            try:
                _ = self.driver.current_url
                # 如果能获取 URL，说明浏览器还在
                self.driver.quit()
                print("✅ 浏览器已关闭")
            except:
                # 浏览器已经关闭
                print("✅ 浏览器已关闭（或已被手动关闭）")
        except Exception as e:
            print(f"⚠️ 关闭浏览器时出错: {e}")


def main():
    print("=" * 60)
    print("          📧 Outlook 邮箱自动注册脚本（功能测试专用）")
    print("          ⚠️  仅用于合法测试，请遵守微软服务条款")
    print("=" * 60)

    registrar = OutlookRegistration()
    should_close_browser = True

    try:
        result = registrar.register()
        if result:
            print("\n🎉 注册流程完成！")
            should_close_browser = True
        else:
            print("\n❌ 注册失败，请检查网络、验证码或页面结构变化。")
            should_close_browser = False  # 保持浏览器打开以便调试
    except KeyboardInterrupt:
        print("\n\n👋 用户中断操作。")
        should_close_browser = False  # 保持浏览器打开
    except Exception as e:
        print(f"\n💥 程序异常: {e}")
        should_close_browser = False  # 保持浏览器打开以便调试
    finally:
        if should_close_browser:
            registrar.close()
        else:
            print("\n" + "="*70)
            print("⏸️  浏览器保持打开，按 Ctrl+C 退出程序")
            print("="*70)
            try:
                # 保持程序运行，让用户可以检查浏览器
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 关闭浏览器...")
                registrar.close()


if __name__ == "__main__":
    main()
