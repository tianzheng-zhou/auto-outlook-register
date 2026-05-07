# -*- coding: utf-8 -*-
"""
代理管理模块
支持代理轮换、IP轮换、代理池管理
"""
import random
import threading
from typing import Optional, List, Dict
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class ProxyConfig:
    """代理配置"""
    protocol: str  # http, https, socks5
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    
    def to_url(self) -> str:
        """转换为代理URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def to_chrome_proxy(self) -> str:
        """转换为Chrome代理格式（用于--proxy-server参数）"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyManager:
    """代理管理器 - 支持代理池和轮换"""
    
    def __init__(self):
        """初始化代理管理器"""
        self.proxy_pool: List[ProxyConfig] = []
        self.current_proxy_index = 0
        self.lock = threading.Lock()
        logger.info("✅ 代理管理器初始化完成")
    
    def add_proxy(self, proxy: ProxyConfig) -> None:
        """添加代理到池中"""
        with self.lock:
            self.proxy_pool.append(proxy)
            logger.info(f"✅ 添加代理: {proxy.to_chrome_proxy()}")
    
    def add_proxies(self, proxies: List[ProxyConfig]) -> None:
        """批量添加代理"""
        with self.lock:
            self.proxy_pool.extend(proxies)
            logger.info(f"✅ 添加 {len(proxies)} 个代理")
    
    def add_proxies_from_list(self, proxy_list: List[str]) -> None:
        """从字符串列表添加代理
        
        格式支持：
        - http://host:port
        - http://username:password@host:port
        - socks5://host:port
        """
        proxies = []
        for proxy_str in proxy_list:
            try:
                proxy = self._parse_proxy_string(proxy_str)
                proxies.append(proxy)
            except Exception as e:
                logger.warning(f"⚠️  解析代理失败: {proxy_str}, 错误: {e}")
        
        if proxies:
            self.add_proxies(proxies)
    
    def _parse_proxy_string(self, proxy_str: str) -> ProxyConfig:
        """解析代理字符串"""
        # 移除空格
        proxy_str = proxy_str.strip()
        
        # 提取协议
        if "://" in proxy_str:
            protocol, rest = proxy_str.split("://", 1)
        else:
            protocol = "http"
            rest = proxy_str
        
        # 提取用户名密码
        username = None
        password = None
        if "@" in rest:
            auth, host_port = rest.rsplit("@", 1)
            if ":" in auth:
                username, password = auth.split(":", 1)
            else:
                username = auth
        else:
            host_port = rest
        
        # 提取主机和端口
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)
        else:
            raise ValueError(f"无效的代理格式: {proxy_str}")
        
        return ProxyConfig(
            protocol=protocol,
            host=host,
            port=port,
            username=username,
            password=password
        )
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """获取下一个代理（轮换）"""
        with self.lock:
            if not self.proxy_pool:
                return None
            
            proxy = self.proxy_pool[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_pool)
            return proxy
    
    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """获取随机代理"""
        with self.lock:
            if not self.proxy_pool:
                return None
            return random.choice(self.proxy_pool)
    
    def get_proxy_count(self) -> int:
        """获取代理数量"""
        with self.lock:
            return len(self.proxy_pool)
    
    def remove_proxy(self, proxy_url: str) -> bool:
        """删除指定的代理"""
        with self.lock:
            for i, proxy in enumerate(self.proxy_pool):
                if proxy.to_url() == proxy_url:
                    self.proxy_pool.pop(i)
                    if self.current_proxy_index >= len(self.proxy_pool) and self.proxy_pool:
                        self.current_proxy_index = 0
                    logger.info(f"✅ 删除代理: {proxy_url}")
                    return True
            logger.warning(f"⚠️ 代理未找到: {proxy_url}")
            return False

    def clear_proxies(self) -> None:
        """清空代理池"""
        with self.lock:
            self.proxy_pool.clear()
            self.current_proxy_index = 0
            logger.info("✅ 代理池已清空")


# 全局代理管理器实例
_proxy_manager_instance: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """获取全局代理管理器实例"""
    global _proxy_manager_instance
    if _proxy_manager_instance is None:
        _proxy_manager_instance = ProxyManager()
    return _proxy_manager_instance

