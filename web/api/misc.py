# -*- coding: utf-8 -*-
"""
杂项 API
========

- /api/health           健康检查（已经在 server.py 里有，这里复用一下）
- /api/accounts         Augment 账号列表（注册页 + 账号管理页都用）
- /api/accounts/{id}    更新 / 删除单个账号
- /api/proxies/status   仅暴露代理池数量给顶部状态条
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import logger


router = APIRouter(tags=["misc"])


# ============================== 模型 ==============================

class UpdateAccountReq(BaseModel):
    status: str | None = None
    notes: str | None = None
    plan_name: str | None = None
    credits: int | None = None
    total_credits: int | None = None
    used_credits: int | None = None
    card_bound: int | None = None
    card_number_masked: str | None = None
    tenant_url: str | None = None


def _account_to_dict(acc: Any) -> Dict[str, Any]:
    """AugmentAccount → dict（前端需要的字段子集）"""
    return {
        "id": acc.id,
        "email": acc.email,
        "password": acc.password,
        "tenant_url": acc.tenant_url,
        "status": acc.status,
        "credits": acc.credits,
        "total_credits": acc.total_credits,
        "used_credits": acc.used_credits,
        "plan_name": acc.plan_name,
        "card_bound": acc.card_bound,
        "card_number_masked": acc.card_number_masked,
        "registered_at": acc.registered_at,
        "last_updated_at": acc.last_updated_at,
        "notes": acc.notes,
    }


# ============================== 账号 ==============================

@router.get("/api/accounts")
async def list_accounts(status: str | None = None) -> Dict[str, Any]:
    """Augment 账号列表"""
    try:
        from database.augment_db_manager import AugmentDBManager
        db = AugmentDBManager()
        rows = db.get_all_accounts(status=status) if status else db.get_all_accounts()
        return {
            "ok": True,
            "count": len(rows),
            "items": [_account_to_dict(r) for r in rows],
        }
    except Exception as e:
        logger.error(f"列出账号失败: {e}")
        raise HTTPException(500, str(e))


@router.put("/api/accounts/{account_id}")
async def update_account(account_id: int, req: UpdateAccountReq) -> Dict[str, Any]:
    """更新账号字段（只更新非 None 字段）"""
    try:
        from database.augment_db_manager import AugmentDBManager
        db = AugmentDBManager()
        kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
        if not kwargs:
            raise HTTPException(400, "没有要更新的字段")
        ok = db.update_account(account_id, **kwargs)
        return {"ok": bool(ok)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新账号失败: {e}")
        raise HTTPException(500, str(e))


@router.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int) -> Dict[str, Any]:
    try:
        from database.augment_db_manager import AugmentDBManager
        db = AugmentDBManager()
        ok = db.delete_account(account_id)
        return {"ok": bool(ok)}
    except Exception as e:
        logger.error(f"删除账号失败: {e}")
        raise HTTPException(500, str(e))


# /api/proxies/status 已迁到 web/api/proxies.py
