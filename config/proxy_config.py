# -*- coding: utf-8 -*-
"""
代理配置文件
支持多种代理格式和轮换策略
"""

# ==================== 代理列表 ====================
# 格式支持：
# - http://host:port
# - http://username:password@host:port
# - socks5://host:port
# - socks5://username:password@host:port

PROXY_LIST = [
    # 示例代理（需要替换为真实代理）
    # "http://proxy1.example.com:8080",
    # "http://user:pass@proxy2.example.com:8080",
    # "socks5://proxy3.example.com:1080",
]

# ==================== 代理轮换策略 ====================
# 'round_robin': 轮询（按顺序轮换）
# 'random': 随机选择
PROXY_ROTATION_STRATEGY = 'round_robin'

# ==================== 代理超时设置 ====================
# 代理连接超时（秒）
PROXY_CONNECT_TIMEOUT = 10

# 代理读取超时（秒）
PROXY_READ_TIMEOUT = 30

# ==================== 代理验证 ====================
# 是否在启动时验证代理可用性
VERIFY_PROXY_ON_STARTUP = False

# 代理验证URL（用于测试代理是否可用）
PROXY_TEST_URL = "http://httpbin.org/ip"

# ==================== 使用说明 ====================
"""
1. 添加代理到PROXY_LIST中
2. 在Augment Tab中配置代理
3. 系统会自动轮换代理

示例：
PROXY_LIST = [
    "http://192.168.1.100:8080",
    "http://user:password@192.168.1.101:8080",
    "socks5://192.168.1.102:1080",
]

注意：
- 确保代理服务器正常运行
- 代理应该支持HTTP/HTTPS和SOCKS5
- 建议使用住宅IP代理而不是数据中心IP代理
- 不同的代理应该来自不同的IP地址
"""

