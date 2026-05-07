# -*- coding: utf-8 -*-
"""
代理检测模块 - 检测代理IP和地理位置
"""
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    import requests

from contextlib import contextmanager
from typing import Optional, Dict, Tuple
from utils.logger import logger


@contextmanager
def _maybe_chain_proxy(proxy_url: str, use_upstream: Optional[bool]):
    """
    根据链式代理配置，临时把 proxy_url 替换为指向本地中转的 URL。

    yield 出最终用于检测的 proxy_url。退出时关闭临时启动的中转 server。

    Args:
        proxy_url: 下游（住宅）代理 URL
        use_upstream:
            - None：读 chain_settings，按用户配置决定
            - True：强制启用
            - False：强制禁用
    """
    chain_server = None
    effective_url = proxy_url
    try:
        # 决定是否启用上游
        upstream_url: Optional[str] = None
        if use_upstream is False:
            upstream_url = None
        else:
            try:
                from config.proxy_chain_settings import load_chain_settings
                settings = load_chain_settings()
                if (use_upstream is True) or settings.get("enabled"):
                    upstream_url = settings.get("upstream_url") or None
            except Exception as e:
                logger.debug(f"读取链式代理配置失败，按禁用处理: {e}")
                upstream_url = None

        if upstream_url:
            try:
                from .proxy_manager import ProxyManager
                from .proxy_chain import ChainedProxyServer
                pm = ProxyManager()
                up_cfg = pm._parse_proxy_string(upstream_url)
                down_cfg = pm._parse_proxy_string(proxy_url)
                chain_server = ChainedProxyServer(upstream=up_cfg, downstream=down_cfg)
                chain_server.start()
                effective_url = chain_server.local_url
                logger.info(
                    f"🔗 检测时启用链式代理：{effective_url} → 上游 {up_cfg.host}:{up_cfg.port} → 下游 {down_cfg.host}:{down_cfg.port}"
                )
            except Exception as e:
                logger.warning(f"⚠️ 启动链式中转失败，将直连下游代理: {e}")
                chain_server = None
                effective_url = proxy_url

        yield effective_url
    finally:
        if chain_server is not None:
            try:
                chain_server.stop()
            except Exception:
                pass


class ProxyDetector:
    """代理检测器 - 检测代理IP和地理位置"""

    # 多个IP检测API（备选方案）
    APIS = [
        'http://ip-api.com/json/',
        'https://ipinfo.io/json',
        'https://ipapi.co/json/',
    ]

    @staticmethod
    def detect_proxy_info(proxy_url: str,
                          timeout: int = 10,
                          use_upstream: Optional[bool] = None) -> Optional[Dict]:
        """
        检测代理信息（IP、位置、AS号码、商家等）

        Args:
            proxy_url: 代理URL (e.g., "http://host:port" 或 "socks5://host:port")
            timeout: 超时时间（秒）
            use_upstream:
                - None（默认）：读全局链式代理配置自动决定
                - True：强制启用上游链式代理
                - False：强制不使用上游

        Returns:
            {
                'ip': '109.166.36.159',
                'location': '日本 东京 东京',
                'as_number': 'AS212238',
                'provider': 'Digital Virtualisation Solutions Tokyo',
                'country': 'Japan',
                'city': 'Tokyo',
                'timezone': 'Asia/Tokyo',
                'success': True
            }
        """
        try:
            logger.info(f"🔍 正在检测代理: {proxy_url[:50]}...")

            with _maybe_chain_proxy(proxy_url, use_upstream) as effective_url:
                # 如果有 httpx，优先使用 httpx（对 SOCKS5 支持更好）
                if HAS_HTTPX:
                    return ProxyDetector._detect_with_httpx(effective_url, timeout)
                else:
                    return ProxyDetector._detect_with_requests(effective_url, timeout)

        except Exception as e:
            logger.error(f"❌ 代理检测失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _detect_with_httpx(proxy_url: str, timeout: int) -> Optional[Dict]:
        """使用 httpx 库检测代理（对 SOCKS5 支持更好）"""
        try:
            with httpx.Client(proxy=proxy_url, timeout=timeout) as client:
                # 尝试多个API
                for api_url in ProxyDetector.APIS:
                    try:
                        logger.info(f"📡 尝试API (httpx): {api_url}")
                        response = client.get(api_url)

                        if response.status_code == 200:
                            data = response.json()
                            # 交给 _parse_api_response 识别各 API 的响应格式（ip-api / ipinfo / ipapi.co）
                            result = ProxyDetector._parse_api_response(data, api_url)
                            if result and result.get('success'):
                                logger.info(f"✅ 检测成功 (httpx): IP={result.get('ip')}, 位置={result.get('location')}")
                                return result
                            else:
                                logger.warning(f"⚠️ {api_url} 返回 200 但响应无法解析: keys={list(data.keys())[:6]}")
                        else:
                            logger.warning(f"⚠️ {api_url} 返回状态码: {response.status_code}")

                    except Exception as e:
                        logger.warning(f"⚠️ {api_url} 错误 ({type(e).__name__}): {e}")
                        continue

            # 所有API都失败了
            logger.error(f"❌ 所有API都失败了 (httpx)")
            return {
                'success': False,
                'error': 'All APIs failed'
            }

        except Exception as e:
            logger.warning(f"⚠️ httpx 检测失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _detect_with_requests(proxy_url: str, timeout: int) -> Optional[Dict]:
        """使用 requests 库检测代理（备选方案）"""
        try:
            # 转换代理格式
            proxies = {
                'http': proxy_url,
                'https': proxy_url,
            }

            # 尝试多个API
            for api_url in ProxyDetector.APIS:
                try:
                    logger.info(f"📡 尝试API (requests): {api_url}")
                    response = requests.get(
                        api_url,
                        proxies=proxies,
                        timeout=timeout,
                        verify=False
                    )

                    if response.status_code == 200:
                        data = response.json()
                        # 交给 _parse_api_response 识别各 API 的响应格式（ip-api / ipinfo / ipapi.co）
                        result = ProxyDetector._parse_api_response(data, api_url)
                        if result and result.get('success'):
                            logger.info(f"✅ 检测成功 (requests): IP={result.get('ip')}, 位置={result.get('location')}")
                            return result
                        else:
                            logger.warning(f"⚠️ {api_url} 返回 200 但响应无法解析: keys={list(data.keys())[:6]}")
                    else:
                        logger.warning(f"⚠️ {api_url} 返回状态码: {response.status_code}")

                except Exception as e:
                    logger.warning(f"⚠️ {api_url} 错误 ({type(e).__name__}): {e}")
                    continue

            # 所有API都失败了
            logger.error(f"❌ 所有API都失败了 (requests)")
            return {
                'success': False,
                'error': 'All APIs failed'
            }

        except Exception as e:
            logger.warning(f"⚠️ requests 检测失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _parse_api_response(data: dict, api_url: str) -> Optional[Dict]:
        """
        解析不同API的响应格式
        """
        try:
            # ip-api.com 格式
            if 'query' in data:
                ip = data.get('query', '')
                country = data.get('country', '')
                region = data.get('regionName', '')
                city = data.get('city', '')
                timezone = data.get('timezone', '')
                isp = data.get('isp', '')
                org = data.get('org', '')
                as_info = data.get('as', '')

                # 构建位置字符串
                location_parts = [country, region, city]
                location = ' '.join([p for p in location_parts if p])

                # 提取AS号码
                as_number = as_info.split()[0] if as_info else ''

                # 提取商家名称
                provider = ' '.join(as_info.split()[1:]) if as_info else isp or org

                return {
                    'ip': ip,
                    'location': location,
                    'country': country,
                    'city': city,
                    'timezone': timezone,
                    'as_number': as_number,
                    'provider': provider,
                    'success': True
                }

            # ipinfo.io 格式
            elif 'ip' in data:
                ip = data.get('ip', '')
                location = data.get('city', '')
                country = data.get('country', '')
                timezone = data.get('timezone', '')
                org = data.get('org', '')

                # 提取AS号码和商家
                as_number = ''
                provider = org
                if org:
                    parts = org.split()
                    if parts[0].startswith('AS'):
                        as_number = parts[0]
                        provider = ' '.join(parts[1:])

                return {
                    'ip': ip,
                    'location': location,
                    'country': country,
                    'timezone': timezone,
                    'as_number': as_number,
                    'provider': provider,
                    'success': True
                }

            # ipapi.co 格式
            elif 'ip' in data and 'city' in data:
                ip = data.get('ip', '')
                location = data.get('city', '')
                country = data.get('country_name', '')
                timezone = data.get('timezone', '')
                org = data.get('org', '')

                # 提取AS号码和商家
                as_number = ''
                provider = org
                if org:
                    parts = org.split()
                    if parts[0].startswith('AS'):
                        as_number = parts[0]
                        provider = ' '.join(parts[1:])

                return {
                    'ip': ip,
                    'location': location,
                    'country': country,
                    'timezone': timezone,
                    'as_number': as_number,
                    'provider': provider,
                    'success': True
                }

            return None

        except Exception as e:
            logger.warning(f"⚠️ 解析API响应失败: {e}")
            return None
    
    @staticmethod
    def test_proxy_connection(proxy_url: str, timeout: int = 5) -> Tuple[bool, str]:
        """
        测试代理连接是否正常
        
        Args:
            proxy_url: 代理URL
            timeout: 超时时间（秒）
        
        Returns:
            (是否连接成功, 消息)
        """
        try:
            proxies = {
                'http': proxy_url,
                'https': proxy_url,
            }
            
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxies,
                timeout=timeout,
                verify=False
            )
            
            if response.status_code == 200:
                logger.info(f"✅ 代理连接正常: {proxy_url[:50]}...")
                return True, "代理连接正常"
            else:
                logger.warning(f"⚠️ 代理返回异常状态码: {response.status_code}")
                return False, f"异常状态码: {response.status_code}"
        
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ 代理连接超时: {proxy_url[:50]}...")
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ 代理连接失败: {proxy_url[:50]}...")
            return False, "连接失败"
        except Exception as e:
            logger.error(f"❌ 代理测试失败: {e}")
            return False, str(e)

