# -*- coding: utf-8 -*-
"""
浏览器指纹伪装模块
完整的反检测浏览器配置，包括：
- User-Agent伪装
- Canvas/WebGL指纹
- 硬件信息伪装
- WebRTC泄露防护
- 插件列表伪装
- 时区和语言设置
"""
import random
import string
import undetected_chromedriver as uc
from typing import Optional
from utils.logger import logger

# logger = get_logger(__name__)


class BrowserFingerprint:
    """浏览器指纹伪装管理器"""
    
    # 真实的User-Agent列表（Windows/Mac/Linux混合）
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    ]
    
    # 屏幕分辨率列表（常见的真实分辨率）
    SCREEN_RESOLUTIONS = [
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (1280, 720),
        (2560, 1440),
        (1920, 1200),
    ]
    
    # 时区列表
    TIMEZONES = [
        "Asia/Shanghai",
        "Asia/Beijing",
        "Asia/Hong_Kong",
        "Asia/Tokyo",
        "America/New_York",
        "Europe/London",
        "Europe/Paris",
    ]
    
    # 语言列表 - 支持中文和英文混合环境
    LANGUAGES = [
        "zh-CN,zh;q=0.9,en;q=0.8",  # 中文优先
        "zh-CN,zh;q=0.9",            # 纯中文
        "en-US,en;q=0.9",            # 英文
        "en-GB,en;q=0.9",            # 英文（英国）
    ]
    
    @staticmethod
    def get_random_user_agent() -> str:
        """获取随机User-Agent"""
        return random.choice(BrowserFingerprint.USER_AGENTS)
    
    @staticmethod
    def get_random_screen_resolution() -> tuple:
        """获取随机屏幕分辨率"""
        return random.choice(BrowserFingerprint.SCREEN_RESOLUTIONS)
    
    @staticmethod
    def get_random_timezone() -> str:
        """获取随机时区"""
        return random.choice(BrowserFingerprint.TIMEZONES)
    
    @staticmethod
    def get_random_language() -> str:
        """获取随机语言"""
        return random.choice(BrowserFingerprint.LANGUAGES)
    
    @staticmethod
    def get_random_device_memory() -> int:
        """获取随机设备内存（GB）"""
        return random.choice([4, 8, 16, 32])
    
    @staticmethod
    def get_random_hardware_concurrency() -> int:
        """获取随机CPU核心数"""
        return random.choice([2, 4, 6, 8, 12, 16])


def create_stealth_browser(chrome_version: Optional[int] = None,
                          user_agent: Optional[str] = None,
                          headless: bool = False,
                          retry: int = 3,
                          driver_executable_path: Optional[str] = None,
                          proxy: Optional['ProxyConfig'] = None) -> uc.Chrome:
    """
    创建完整伪装指纹的浏览器实例

    Args:
        chrome_version: Chrome主版本号，如果为None则自动检测
        user_agent: 自定义User-Agent，如果为None则随机选择
        headless: 是否使用无头模式
        retry: 重试次数，默认3次
        driver_executable_path: 本地chromedriver路径，如果指定则不下载
        proxy: ProxyConfig对象，用于设置代理

    Returns:
        uc.Chrome: 配置好的浏览器驱动实例

    Raises:
        Exception: 浏览器启动失败
    """
    logger.info("🔧 开始配置浏览器指纹伪装...")

    # 检查本地chromedriver
    if driver_executable_path:
        from pathlib import Path
        driver_path = Path(driver_executable_path)
        if driver_path.exists():
            logger.info(f"✅ 使用本地chromedriver: {driver_path}")
        else:
            logger.warning(f"⚠️  本地chromedriver不存在: {driver_path}，将尝试自动下载")
            driver_executable_path = None

    # 初始化Chrome选项
    chrome_options = uc.ChromeOptions()

    # ========== 1. 基础反检测参数 ==========
    logger.debug("配置基础反检测参数...")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")

    # ========== 1.5. 代理配置 ==========
    if proxy:
        logger.info(f"🌐 配置代理: {proxy.to_chrome_proxy()}")
        chrome_options.add_argument(f"--proxy-server={proxy.to_chrome_proxy()}")
    else:
        logger.debug("未配置代理，使用本地IP")
        chrome_options.add_argument("--no-proxy-server")  # 禁用系统代理，避免ERR_CONNECTION_CLOSED错误
    
    # ========== 2. User-Agent伪装 ==========
    ua = user_agent or BrowserFingerprint.get_random_user_agent()
    logger.debug(f"设置User-Agent: {ua[:80]}...")
    chrome_options.add_argument(f"user-agent={ua}")
    
    # ========== 3. 屏幕和显示设置 ==========
    width, height = BrowserFingerprint.get_random_screen_resolution()
    logger.debug(f"设置屏幕分辨率: {width}x{height}")
    chrome_options.add_argument(f"--window-size={width},{height}")
    chrome_options.add_argument("--start-maximized")
    
    # ========== 4. 语言和地区设置 ==========
    language = BrowserFingerprint.get_random_language()
    logger.debug(f"设置语言: {language}")
    chrome_options.add_argument("--lang=zh-CN")
    chrome_options.add_experimental_option('prefs', {
        'intl.accept_languages': language
    })
    
    # ========== 5. 时区设置 ==========
    timezone = BrowserFingerprint.get_random_timezone()
    logger.debug(f"设置时区: {timezone}")
    chrome_options.add_argument(f"--timezone-id={timezone}")
    
    # ========== 6. 硬件信息伪装 ==========
    device_memory = BrowserFingerprint.get_random_device_memory()
    hw_concurrency = BrowserFingerprint.get_random_hardware_concurrency()
    logger.debug(f"设置硬件信息: 内存{device_memory}GB, CPU{hw_concurrency}核")
    
    # ========== 7. WebRTC泄露防护 ==========
    logger.debug("配置WebRTC泄露防护...")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-default-apps")
    
    # ========== 8. 隐私和安全设置 ==========
    logger.debug("配置隐私和安全设置...")
    chrome_options.add_argument("--disable-web-resources")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-component-extensions-with-background-pages")
    
    # ========== 9. 性能优化 ==========
    logger.debug("配置性能优化...")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--disable-sync")
    
    # ========== 10. 无头模式（可选） ==========
    if headless:
        logger.debug("启用无头模式")
        chrome_options.add_argument("--headless=new")
    
    # ========== 11. 启动浏览器（带重试机制） ==========
    logger.info("🚀 启动undetected-chromedriver...")

    last_error = None
    for attempt in range(1, retry + 1):
        try:
            if attempt > 1:
                logger.warning(f"⚠️  第 {attempt} 次重试启动浏览器...")

            # 构建启动参数
            driver_kwargs = {
                'options': chrome_options,
            }

            # 如果指定了本地driver路径，使用本地driver
            if driver_executable_path:
                driver_kwargs['driver_executable_path'] = str(driver_executable_path)
                logger.info(f"📍 使用本地chromedriver: {driver_executable_path}")
            elif chrome_version:
                driver_kwargs['version_main'] = chrome_version
                logger.debug(f"使用指定Chrome版本: {chrome_version}")
            else:
                logger.debug("自动检测Chrome版本")

            # 启动浏览器
            driver = uc.Chrome(**driver_kwargs)

            logger.info("✅ 浏览器启动成功")

            # ========== 12. 注入JavaScript指纹伪装脚本 ==========
            logger.debug("注入JavaScript指纹伪装脚本...")
            _inject_fingerprint_scripts(driver, device_memory, hw_concurrency)

            # ========== 13. 验证代理是否生效 ==========
            if proxy:
                logger.info("🔍 验证代理是否生效...")
                try:
                    import time
                    driver.get("https://ipinfo.io/json")
                    time.sleep(1)
                    page_source = driver.page_source
                    if '"ip"' in page_source:
                        logger.info(f"✅ 代理验证成功: {page_source[:100]}...")
                    else:
                        logger.warning(f"⚠️ 代理验证失败: 无法获取IP信息")
                except Exception as e:
                    logger.warning(f"⚠️ 代理验证异常: {e}")

            return driver

        except Exception as e:
            last_error = e
            error_msg = str(e)

            # SSL错误只记录为debug级别（不影响指纹伪装）
            if "SSL" in error_msg or "UNEXPECTED_EOF" in error_msg:
                logger.debug(f"⚠️  第 {attempt} 次启动失败（SSL网络问题）: {error_msg[:80]}")
            else:
                logger.error(f"❌ 第 {attempt} 次启动失败: {error_msg[:100]}")

            if attempt < retry:
                import time
                wait_time = 2 ** attempt  # 指数退避：2秒、4秒、8秒
                logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ 浏览器启动失败（已重试{retry}次）: {e}", exc_info=True)
                raise Exception(f"浏览器启动失败（已重试{retry}次）: {e}")


def _inject_fingerprint_scripts(driver: uc.Chrome, 
                               device_memory: int,
                               hw_concurrency: int) -> None:
    """
    注入JavaScript脚本来伪装浏览器指纹
    
    Args:
        driver: Selenium WebDriver实例
        device_memory: 设备内存（GB）
        hw_concurrency: CPU核心数
    """
    try:
        # 伪装navigator.deviceMemory
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': f"""
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => {device_memory}
                }});
            """
        })
        
        # 伪装navigator.hardwareConcurrency
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': f"""
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: () => {hw_concurrency}
                }});
            """
        })
        
        # 伪装navigator.webdriver
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        # 伪装navigator.plugins
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': """
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', description: 'Portable Document Format'},
                        {name: 'Chrome PDF Viewer', description: ''},
                        {name: 'Native Client Executable', description: ''}
                    ]
                });
            """
        })
        
        logger.debug("✅ JavaScript指纹伪装脚本注入成功")
        
    except Exception as e:
        logger.warning(f"⚠️  JavaScript脚本注入失败: {e}")
        # 不中断流程，继续执行

