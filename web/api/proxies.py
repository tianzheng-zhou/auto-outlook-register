# -*- coding: utf-8 -*-
"""
代理 API
========

- /api/proxies                列表 (GET) / 批量添加并检测 (POST) / 清空 (DELETE)
- /api/proxies/{id}           单个删除 / 单个重新检测
- /api/proxies/use-one        使用选中的代理（清空池后只放 1 个）
- /api/proxies/use-all        全部加入池（轮换模式）
- /api/proxies/chain          GET 当前链式代理设置 / PUT 保存

注意：代理检测可能耗时（每个 ~5-10s），所以 POST /api/proxies 是同步执行
后返回完整结果。前端需要给个 loading 提示。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import logger


router = APIRouter(prefix="/api/proxies", tags=["proxies"])


# ============================== 模型 ==============================

class AddProxiesReq(BaseModel):
    text: str          # 多行代理串，每行一个
    detect: bool = True  # 是否同步检测


class ProxyIdsReq(BaseModel):
    ids: List[int]


class UseOneReq(BaseModel):
    proxy_id: int


# ============================== 链式代理设置 ==============================

class ChainSettingsReq(BaseModel):
    enabled: bool
    upstream_url: str


# 注意：FastAPI 路由匹配按定义顺序，先静态路径后动态。
# /chain 必须放在 /{proxy_id} 之前


@router.get("/chain")
async def get_chain_settings() -> Dict[str, Any]:
    from config.proxy_chain_settings import load_chain_settings
    s = load_chain_settings()
    return {"ok": True, "settings": s}


@router.put("/chain")
async def put_chain_settings(req: ChainSettingsReq) -> Dict[str, Any]:
    from config.proxy_chain_settings import save_chain_settings
    save_chain_settings({"enabled": bool(req.enabled), "upstream_url": req.upstream_url.strip()})
    return {"ok": True}


# ============================== 列表 / 添加 / 清空 ==============================

def _proxy_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """数据库行 → 前端 friendly dict"""
    return {
        "id": row.get("id"),
        "protocol": row.get("protocol"),
        "host": row.get("host"),
        "port": row.get("port"),
        "username": row.get("username"),
        "password": row.get("password"),
        "proxy_url": row.get("proxy_url"),
        "ip_address": row.get("ip_address"),
        "location": row.get("location"),
        "as_number": row.get("as_number"),
        "provider": row.get("provider"),
        "is_valid": row.get("is_valid"),
        "last_checked": row.get("last_checked"),
    }


@router.get("")
async def list_proxies() -> Dict[str, Any]:
    """所有代理 + 当前运行时池信息"""
    from database.augment_db_manager import AugmentDBManager
    from core.proxy import get_proxy_manager

    db = AugmentDBManager()
    rows = db.get_all_proxies()
    pm = get_proxy_manager()

    # 取池中代理的 url 列表，标记列表里哪些代理已在池中
    in_pool = set()
    try:
        for p in pm.proxy_pool:
            in_pool.add(p.to_url())
    except Exception:
        pass

    items = []
    for r in rows:
        d = _proxy_to_dict(r)
        d["in_pool"] = d.get("proxy_url") in in_pool
        items.append(d)

    return {
        "ok": True,
        "count": len(items),
        "pool_count": pm.get_proxy_count(),
        "items": items,
    }


@router.post("")
async def add_proxies(req: AddProxiesReq) -> Dict[str, Any]:
    """
    批量添加代理。每行一个（支持各种 socks5/http 格式）。
    detect=True 时会同步对每个代理做一次 IP 检测，**可能比较慢**。
    """
    from core.proxy import ProxyDetector, get_proxy_manager
    from core.proxy.proxy_manager import ProxyConfig
    from database.augment_db_manager import AugmentDBManager

    db = AugmentDBManager()
    pm = get_proxy_manager()

    raw_lines = [ln.strip() for ln in (req.text or "").splitlines() if ln.strip()]
    if not raw_lines:
        raise HTTPException(400, "未提供任何代理行")

    success_ids: List[int] = []
    failures: List[Dict[str, str]] = []

    for line in raw_lines:
        try:
            cfg: ProxyConfig = pm._parse_proxy_string(line)
        except Exception as e:
            failures.append({"line": line, "error": f"解析失败: {e}"})
            continue

        ip = location = as_no = provider = None
        if req.detect:
            try:
                logger.info(f"🔍 正在检测代理: {cfg.to_url()[:50]}...")
                # detector 内部会用链式代理（如启用）
                result = ProxyDetector.detect_proxy_info(cfg.to_url())
                if result and result.get("success"):
                    ip       = result.get("ip")
                    location = result.get("location")
                    as_no    = result.get("as_number")
                    provider = result.get("provider")
                else:
                    logger.warning(
                        f"⚠️ 代理检测失败: {cfg.to_url()[:50]} - {result.get('error') if result else 'no result'}"
                    )
            except Exception as e:
                logger.warning(f"⚠️ 代理检测异常: {e}")

        try:
            pid = db.add_proxy(
                protocol=cfg.protocol, host=cfg.host, port=cfg.port,
                username=cfg.username, password=cfg.password,
                ip_address=ip, location=location,
                as_number=as_no, provider=provider,
            )
            success_ids.append(pid)
        except Exception as e:
            failures.append({"line": line, "error": f"入库失败: {e}"})

    return {
        "ok": True,
        "success_count": len(success_ids),
        "fail_count": len(failures),
        "failures": failures,
    }


@router.delete("")
async def clear_proxies() -> Dict[str, Any]:
    """清空所有代理（数据库 + 运行时池）"""
    from database.augment_db_manager import AugmentDBManager
    from core.proxy import get_proxy_manager

    db = AugmentDBManager()
    db.clear_proxies()
    get_proxy_manager().clear_proxies()
    return {"ok": True}


@router.get("/status")
async def proxies_status() -> Dict[str, Any]:
    """顶部状态条用：当前运行时池里有多少个代理"""
    from core.proxy import get_proxy_manager
    try:
        pm = get_proxy_manager()
        return {"ok": True, "count": pm.get_proxy_count()}
    except Exception as e:
        logger.warning(f"读代理池数量失败: {e}")
        return {"ok": True, "count": 0}


@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: int) -> Dict[str, Any]:
    """删除单个代理"""
    from database.augment_db_manager import AugmentDBManager

    db = AugmentDBManager()
    ok = db.delete_proxy(proxy_id)
    return {"ok": bool(ok)}


@router.post("/{proxy_id}/recheck")
async def recheck_proxy(proxy_id: int) -> Dict[str, Any]:
    """对单个代理重新检测（同步）"""
    from core.proxy import ProxyDetector
    from database.augment_db_manager import AugmentDBManager

    db = AugmentDBManager()
    row = db.get_proxy_by_id(proxy_id)
    if not row:
        raise HTTPException(404, "代理不存在")

    proxy_url = row["proxy_url"]
    result = ProxyDetector.detect_proxy_info(proxy_url)
    if result and result.get("success"):
        db.update_proxy_info(
            proxy_id,
            ip_address=result.get("ip"),
            location=result.get("location"),
            as_number=result.get("as_number"),
            provider=result.get("provider"),
        )
        return {"ok": True, "result": result}
    return {"ok": False, "error": (result or {}).get("error", "检测失败")}


# ============================== 池管理（运行时） ==============================

@router.post("/use-one")
async def use_one_proxy(req: UseOneReq) -> Dict[str, Any]:
    """单选模式：清空池，仅放入这一个代理"""
    from database.augment_db_manager import AugmentDBManager
    from core.proxy import get_proxy_manager

    db = AugmentDBManager()
    row = db.get_proxy_by_id(req.proxy_id)
    if not row:
        raise HTTPException(404, "代理不存在")
    pm = get_proxy_manager()
    pm.clear_proxies()
    pm.add_proxies_from_list([row["proxy_url"]])
    return {"ok": True, "pool_count": pm.get_proxy_count()}


@router.post("/use-all")
async def use_all_proxies() -> Dict[str, Any]:
    """轮换模式：把数据库里所有代理一次性加到运行时池"""
    from database.augment_db_manager import AugmentDBManager
    from core.proxy import get_proxy_manager

    db = AugmentDBManager()
    rows = db.get_all_proxies()
    proxy_urls = [r["proxy_url"] for r in rows if r.get("proxy_url")]
    if not proxy_urls:
        raise HTTPException(400, "数据库里没有可用代理")

    pm = get_proxy_manager()
    pm.clear_proxies()
    pm.add_proxies_from_list(proxy_urls)

    actual = pm.get_proxy_count()
    skipped = len(proxy_urls) - actual
    return {
        "ok": True,
        "pool_count": actual,
        "tried": len(proxy_urls),
        "skipped": skipped,
    }


@router.post("/clear-pool")
async def clear_pool_only() -> Dict[str, Any]:
    """只清空运行时池（不动数据库）"""
    from core.proxy import get_proxy_manager
    pm = get_proxy_manager()
    pm.clear_proxies()
    return {"ok": True, "pool_count": 0}
