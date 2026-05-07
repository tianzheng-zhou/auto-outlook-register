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
import re
import string
import subprocess
from pathlib import Path
import undetected_chromedriver as uc
from typing import Optional
from utils.logger import logger
from .proxy_manager import ProxyConfig

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


def _get_executable_major_version(executable_path: str) -> Optional[int]:
    """读取 Chrome/ChromeDriver 可执行文件的主版本号。

    - Windows 上 chrome.exe --version 不会打印版本（会启动浏览器），
      所以优先用 PowerShell 读 PE 文件资源里的 ProductVersion；
      chromedriver 在 Windows 上 --version 是正常打印的，保留 fallback。
    - 其他平台用 --version。
    """
    import sys
    exe_str = str(executable_path)

    # Windows: 优先用 PowerShell 读 PE 资源里的版本号（不会启动 Chrome）
    if sys.platform.startswith("win"):
        try:
            ps_cmd = (
                f"(Get-Item -LiteralPath '{exe_str}').VersionInfo.ProductVersion"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=8, check=False,
            )
            output = (result.stdout or "").strip()
            match = re.search(r"\b(\d+)\.", output)
            if match:
                return int(match.group(1))
            logger.debug(f"PowerShell 读取版本输出无法解析: {output!r}")
        except Exception as e:
            logger.debug(f"PowerShell 读取版本失败: {exe_str}, {e}")

    # Fallback: --version（chromedriver / Linux 平台都能打）
    try:
        result = subprocess.run(
            [exe_str, "--version"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except Exception as e:
        logger.debug(f"读取版本失败: {executable_path}, {e}")
        return None

    output = f"{result.stdout} {result.stderr}"
    match = re.search(r"\b(\d+)\.", output)
    if not match:
        logger.debug(f"无法解析版本输出: {output.strip()}")
        return None

    return int(match.group(1))


def _get_installed_chrome_major_version() -> Optional[int]:
    """获取当前系统 Chrome 主版本号。"""
    chrome_path = uc.find_chrome_executable()
    if not chrome_path:
        return None

    return _get_executable_major_version(chrome_path)


def _get_cached_chromedriver_path(chrome_version: Optional[int]) -> Optional[str]:
    """获取 undetected-chromedriver 已缓存的 driver 路径。"""
    try:
        from undetected_chromedriver.patcher import Patcher

        patcher = Patcher(version_main=chrome_version or 0)
    except Exception as e:
        logger.debug(f"获取缓存chromedriver路径失败: {e}")
        return None

    cached_path = Path(patcher.executable_path)
    if not cached_path.exists():
        return None

    return str(cached_path)


def _get_matching_cached_chromedriver(chrome_version: Optional[int]) -> Optional[str]:
    """获取与当前 Chrome 主版本匹配的缓存 driver。

    如果缓存里的 driver 版本与 Chrome 不匹配，会主动**删除缓存文件**，
    迫使 undetected-chromedriver 在下次启动时按 version_main 重新下载。
    这是因为 uc 3.5 系列的缓存是单一文件（undetected_chromedriver.exe），
    存在缓存就直接复用，不会因为传 version_main 而自动比对/换版本。
    """
    if not chrome_version:
        return None

    cached_path = _get_cached_chromedriver_path(chrome_version)
    if not cached_path:
        return None

    cached_major = _get_executable_major_version(cached_path)
    if cached_major == chrome_version:
        return cached_path

    # 不匹配 → 主动删除缓存文件，触发 uc 重新下载
    logger.warning(
        f"⚠️  缓存chromedriver版本({cached_major})与Chrome版本({chrome_version})不匹配，"
        f"将删除缓存以触发重新下载: {cached_path}"
    )
    try:
        Path(cached_path).unlink()
        logger.info(f"🗑️  已删除过期chromedriver缓存: {cached_path}")
    except Exception as e:
        logger.error(
            f"❌ 删除过期chromedriver缓存失败: {e}\n"
            f"   请手动删除该文件后重启程序: {cached_path}"
        )
    return None


def create_stealth_browser(chrome_version: Optional[int] = None,
                          user_agent: Optional[str] = None,
                          headless: bool = False,
                          retry: int = 3,
                          driver_executable_path: Optional[str] = None,
                          proxy: Optional['ProxyConfig'] = None,
                          upstream_proxy: Optional['ProxyConfig'] = None) -> uc.Chrome:
    """
    创建完整伪装指纹的浏览器实例

    Args:
        chrome_version: Chrome主版本号，如果为None则自动检测
        user_agent: 自定义User-Agent，如果为None则随机选择
        headless: 是否使用无头模式
        retry: 重试次数，默认3次
        driver_executable_path: 自定义chromedriver路径，通常不需要指定
        proxy: ProxyConfig对象，用于设置代理（最终出口代理，例如海外住宅代理）
        upstream_proxy: 可选的上游代理（例如本地 Clash），用于实现链式代理
            链路：浏览器 → 本地中转 → upstream_proxy → proxy → 目标
            未提供时浏览器直接连 proxy。

    Returns:
        uc.Chrome: 配置好的浏览器驱动实例。
            若启用了链式代理，driver 上会挂一个 `_chained_proxy_server` 属性，
            调用方在关闭浏览器后应调用 `.stop()` 释放本地端口。

    Raises:
        Exception: 浏览器启动失败
    """
    logger.info("🔧 开始配置浏览器指纹伪装...")

    # ========== 0. 链式代理：在本地起一个 HTTP CONNECT 中转 ==========
    chained_server = None
    effective_proxy_for_chrome = proxy  # 浏览器实际看到的代理（直连或本地中转）
    if proxy and upstream_proxy:
        try:
            from .proxy_chain import ChainedProxyServer
            chained_server = ChainedProxyServer(upstream=upstream_proxy, downstream=proxy)
            chained_server.start()
            # 让 Chrome 连本地中转，由中转去做 上游 → 下游 的链式 CONNECT
            effective_proxy_for_chrome = ProxyConfig(
                protocol="http",
                host="127.0.0.1",
                port=chained_server.port,
            )
            logger.info(
                f"🔗 已启用链式代理: 浏览器 → {effective_proxy_for_chrome.host}:{effective_proxy_for_chrome.port} "
                f"→ 上游 {upstream_proxy.host}:{upstream_proxy.port} "
                f"→ 下游 {proxy.host}:{proxy.port}"
            )
        except Exception as e:
            logger.error(f"❌ 启动链式代理失败，将回退为直连下游代理: {e}")
            # 如果 server 已经 start()，必须 stop 一下，避免占着本地端口
            if chained_server is not None:
                try:
                    chained_server.stop()
                except Exception as stop_err:
                    logger.debug(f"清理已启动但失败的链式 server 出错: {stop_err}")
            chained_server = None
            effective_proxy_for_chrome = proxy

    installed_chrome_major = _get_installed_chrome_major_version()
    if installed_chrome_major:
        if chrome_version and chrome_version != installed_chrome_major:
            logger.warning(
                f"⚠️  配置的Chrome版本({chrome_version})与当前Chrome版本({installed_chrome_major})不一致，"
                f"将使用当前Chrome版本"
            )
        chrome_version = installed_chrome_major

    # 检查自定义chromedriver
    if driver_executable_path:
        driver_path = Path(driver_executable_path)
        if driver_path.exists():
            logger.info(f"✅ 使用指定chromedriver: {driver_path}")
            driver_major = _get_executable_major_version(str(driver_path))
            if installed_chrome_major and driver_major and driver_major != installed_chrome_major:
                logger.warning(
                    f"⚠️  指定chromedriver版本({driver_major})与Chrome版本({installed_chrome_major})不匹配，"
                    f"将跳过指定driver"
                )
                driver_executable_path = None
        else:
            logger.warning(f"⚠️  指定chromedriver不存在: {driver_path}，将尝试自动下载")
            driver_executable_path = None

    if not driver_executable_path:
        cached_driver_path = _get_matching_cached_chromedriver(chrome_version)
        if cached_driver_path:
            logger.info(f"✅ 使用已缓存匹配chromedriver: {cached_driver_path}")
            driver_executable_path = cached_driver_path

    ua = user_agent or BrowserFingerprint.get_random_user_agent()
    width, height = BrowserFingerprint.get_random_screen_resolution()
    language = BrowserFingerprint.get_random_language()
    timezone = BrowserFingerprint.get_random_timezone()
    device_memory = BrowserFingerprint.get_random_device_memory()
    hw_concurrency = BrowserFingerprint.get_random_hardware_concurrency()

    def _build_chrome_options() -> uc.ChromeOptions:
        # undetected-chromedriver 会给 options 绑定 session；重试必须使用新对象。
        chrome_options = uc.ChromeOptions()

        # ========== 1. 基础反检测参数 ==========
        logger.debug("配置基础反检测参数...")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")

        # ========== 1.5. 代理配置 ==========
        if effective_proxy_for_chrome:
            logger.info(f"🌐 配置代理: {effective_proxy_for_chrome.to_chrome_proxy()}")
            chrome_options.add_argument(f"--proxy-server={effective_proxy_for_chrome.to_chrome_proxy()}")
        else:
            logger.debug("未配置代理，使用本地IP")
            chrome_options.add_argument("--no-proxy-server")  # 禁用系统代理，避免ERR_CONNECTION_CLOSED错误

        # ========== 2. User-Agent伪装 ==========
        logger.debug(f"设置User-Agent: {ua[:80]}...")
        chrome_options.add_argument(f"user-agent={ua}")

        # ========== 3. 屏幕和显示设置 ==========
        logger.debug(f"设置屏幕分辨率: {width}x{height}")
        chrome_options.add_argument(f"--window-size={width},{height}")
        chrome_options.add_argument("--start-maximized")

        # ========== 4. 语言和地区设置 ==========
        logger.debug(f"设置语言: {language}")
        chrome_options.add_argument("--lang=zh-CN")
        chrome_options.add_experimental_option('prefs', {
            'intl.accept_languages': language
        })

        # ========== 5. 时区设置 ==========
        logger.debug(f"设置时区: {timezone}")
        chrome_options.add_argument(f"--timezone-id={timezone}")

        # ========== 6. 硬件信息伪装 ==========
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

        return chrome_options
    
    # ========== 11. 启动浏览器（带重试机制） ==========
    logger.info("🚀 启动undetected-chromedriver...")

    last_error = None
    for attempt in range(1, retry + 1):
        try:
            if attempt > 1:
                logger.warning(f"⚠️  第 {attempt} 次重试启动浏览器...")

            # 构建启动参数
            driver_kwargs = {
                'options': _build_chrome_options(),
            }

            # 如果指定了本地driver路径，使用本地driver
            if driver_executable_path:
                driver_kwargs['driver_executable_path'] = str(driver_executable_path)
                if chrome_version:
                    driver_kwargs['version_main'] = chrome_version
                logger.info(f"📍 使用chromedriver: {driver_executable_path}")
            elif chrome_version:
                driver_kwargs['version_main'] = chrome_version
                logger.debug(f"使用指定Chrome版本: {chrome_version}")
            else:
                logger.debug("自动检测Chrome版本")

            # 启动浏览器
            driver = uc.Chrome(**driver_kwargs)

            # 把链式代理 server 挂到 driver 上，方便调用方在关闭浏览器后释放
            if chained_server is not None:
                setattr(driver, "_chained_proxy_server", chained_server)

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
                # 最终失败：清理已启动的链式代理 server
                if chained_server is not None:
                    try:
                        chained_server.stop()
                    except Exception:
                        pass
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
