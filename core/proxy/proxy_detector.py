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

from typing import Optional, Dict, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class ProxyDetector:
    """代理检测器 - 检测代理IP和地理位置"""

    # 多个IP检测API（备选方案）
    APIS = [
        'http://ip-api.com/json/',
        'https://ipinfo.io/json',
        'https://ipapi.co/json/',
    ]

    @staticmethod
    def detect_proxy_info(proxy_url: str, timeout: int = 10) -> Optional[Dict]:
        """
        检测代理信息（IP、位置、AS号码、商家等）

        Args:
            proxy_url: 代理URL (e.g., "http://host:port" 或 "socks5://host:port")
            timeout: 超时时间（秒）

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

            # 如果有 httpx，优先使用 httpx（对 SOCKS5 支持更好）
            if HAS_HTTPX:
                return ProxyDetector._detect_with_httpx(proxy_url, timeout)
            else:
                return ProxyDetector._detect_with_requests(proxy_url, timeout)

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
                        logger.debug(f"尝试API (httpx): {api_url}")
                        response = client.get(api_url)

                        if response.status_code == 200:
                            data = response.json()

                            # 检查是否是成功的响应
                            if data.get('status') == 'success' or 'query' in data:
                                result = ProxyDetector._parse_api_response(data, api_url)
                                if result and result.get('success'):
                                    logger.info(f"✅ 检测成功 (httpx): IP={result.get('ip')}, 位置={result.get('location')}")
                                    return result

                    except Exception as e:
                        logger.debug(f"⚠️ {api_url} 错误: {e}")
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
                    logger.debug(f"尝试API (requests): {api_url}")
                    response = requests.get(
                        api_url,
                        proxies=proxies,
                        timeout=timeout,
                        verify=False
                    )

                    if response.status_code == 200:
                        data = response.json()

                        # 检查是否是成功的响应
                        if data.get('status') == 'success' or 'query' in data:
                            result = ProxyDetector._parse_api_response(data, api_url)
                            if result and result.get('success'):
                                logger.info(f"✅ 检测成功 (requests): IP={result.get('ip')}, 位置={result.get('location')}")
                                return result

                except Exception as e:
                    logger.debug(f"⚠️ {api_url} 错误: {e}")
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

