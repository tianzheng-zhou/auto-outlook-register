# -*- coding: utf-8 -*-
"""
链式代理（上游代理 / 系统代理）持久化配置

存放在 data/proxy_chain.json，记录：
- enabled:        是否启用链式代理
- upstream_url:   上游代理 URL，例如 http://127.0.0.1:7897

设计为简单 JSON 文件，跨会话保持用户在 GUI 里勾选/输入的值。
"""
from __future__ import annotations

import json
from typing import TypedDict

from config.settings import DATA_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


CONFIG_FILE = DATA_DIR / "proxy_chain.json"

DEFAULT_UPSTREAM_URL = "http://127.0.0.1:7897"


class ChainSettings(TypedDict):
    enabled: bool
    upstream_url: str


def _default_settings() -> ChainSettings:
    return {
        "enabled": False,
        "upstream_url": DEFAULT_UPSTREAM_URL,
    }


def load_chain_settings() -> ChainSettings:
    """加载链式代理设置，文件不存在或损坏时返回默认值"""
    if not CONFIG_FILE.exists():
        return _default_settings()
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return _default_settings()
        return {
            "enabled": bool(raw.get("enabled", False)),
            "upstream_url": str(raw.get("upstream_url") or DEFAULT_UPSTREAM_URL).strip(),
        }
    except Exception as e:
        logger.warning(f"⚠️ 读取链式代理配置失败，使用默认值: {e}")
        return _default_settings()


def save_chain_settings(enabled: bool, upstream_url: str) -> None:
    """保存链式代理设置"""
    data: ChainSettings = {
        "enabled": bool(enabled),
        "upstream_url": (upstream_url or DEFAULT_UPSTREAM_URL).strip(),
    }
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 链式代理配置已保存: enabled={data['enabled']}, upstream={data['upstream_url']}")
    except Exception as e:
        logger.error(f"❌ 保存链式代理配置失败: {e}")
        raise


__all__ = [
    "load_chain_settings",
    "save_chain_settings",
    "DEFAULT_UPSTREAM_URL",
    "ChainSettings",
]
