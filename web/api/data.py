# -*- coding: utf-8 -*-
"""
数据管理 API（邮箱导入 / 列表）
============

- GET    /api/emails            邮箱列表（可按 status 过滤：unused/used/...）
- POST   /api/emails/import     批量导入邮箱（body: {text}）
- DELETE /api/emails/{id}       删除邮箱
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import logger


router = APIRouter(prefix="/api/emails", tags=["data"])


class ImportEmailsReq(BaseModel):
    text: str          # 每行一个邮箱，或者 "邮箱,密码" 格式


@router.get("")
async def list_emails(status: str | None = None) -> Dict[str, Any]:
    from database import DatabaseManager, Email  # noqa
    db = DatabaseManager()
    rows = db.get_all_emails(status=status) if status else db.get_all_emails()
    items = []
    for e in rows:
        items.append({
            "id": e.id,
            "email": e.email,
            "type": getattr(e, "type", None),
            "status": e.status,
            "created_at": getattr(e, "created_at", None),
            "used_at": getattr(e, "used_at", None),
        })
    return {"ok": True, "count": len(items), "items": items}


@router.post("/import")
async def import_emails(req: ImportEmailsReq) -> Dict[str, Any]:
    """
    每行一个邮箱；也支持 `邮箱,密码` 或 `邮箱 | 密码`（额外字段会被忽略）
    """
    from database import DatabaseManager, Email

    db = DatabaseManager()
    lines = [ln.strip() for ln in (req.text or "").splitlines() if ln.strip()]
    if not lines:
        raise HTTPException(400, "未提供任何邮箱")

    success = 0
    failures: List[Dict[str, str]] = []
    for ln in lines:
        # 容错分隔符
        for sep in [",", "|", "\t", " "]:
            if sep in ln:
                addr = ln.split(sep, 1)[0].strip()
                break
        else:
            addr = ln
        if "@" not in addr:
            failures.append({"line": ln, "error": "格式不是邮箱"})
            continue
        try:
            db.add_email(Email(email=addr))
            success += 1
        except Exception as e:
            failures.append({"line": ln, "error": str(e)[:120]})
    return {
        "ok": True,
        "success_count": success,
        "fail_count": len(failures),
        "failures": failures,
    }


@router.delete("/{email_id}")
async def delete_email(email_id: int) -> Dict[str, Any]:
    from database import DatabaseManager
    db = DatabaseManager()
    try:
        db.delete_email(email_id)
        return {"ok": True}
    except Exception as e:
        logger.error(f"删除邮箱失败: {e}")
        raise HTTPException(500, str(e))
