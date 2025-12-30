"""
Augment账号注册系统的数据模型
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class AugmentAccount:
    """Augment账号模型"""
    email: str
    password: Optional[str] = None
    tenant_url: Optional[str] = None
    auth_session: Optional[str] = None
    code: Optional[str] = None
    state: Optional[str] = None
    portal_url: Optional[str] = None
    credits: int = 0
    total_credits: int = 30000
    used_credits: int = 0
    plan_name: str = 'Free Plan'
    next_billing_date: Optional[str] = None
    card_bound: int = 0  # 0: 未绑卡, 1: 已绑卡
    card_number_masked: Optional[str] = None
    status: str = 'registered'  # registered, card_bound, failed, banned
    registered_at: Optional[str] = None
    card_bound_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'email': self.email,
            'password': self.password,
            'tenant_url': self.tenant_url,
            'auth_session': self.auth_session,
            'code': self.code,
            'state': self.state,
            'portal_url': self.portal_url,
            'credits': self.credits,
            'total_credits': self.total_credits,
            'used_credits': self.used_credits,
            'plan_name': self.plan_name,
            'next_billing_date': self.next_billing_date,
            'card_bound': self.card_bound,
            'card_number_masked': self.card_number_masked,
            'status': self.status,
            'registered_at': self.registered_at,
            'card_bound_at': self.card_bound_at,
            'last_updated_at': self.last_updated_at,
            'notes': self.notes,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> 'AugmentAccount':
        """从字典创建"""
        return AugmentAccount(
            id=data.get('id'),
            email=data['email'],
            password=data.get('password'),
            tenant_url=data.get('tenant_url'),
            auth_session=data.get('auth_session'),
            code=data.get('code'),
            state=data.get('state'),
            portal_url=data.get('portal_url'),
            credits=data.get('credits', 0),
            total_credits=data.get('total_credits', 30000),
            used_credits=data.get('used_credits', 0),
            plan_name=data.get('plan_name', 'Free Plan'),
            next_billing_date=data.get('next_billing_date'),
            card_bound=data.get('card_bound', 0),
            card_number_masked=data.get('card_number_masked'),
            status=data.get('status', 'registered'),
            registered_at=data.get('registered_at'),
            card_bound_at=data.get('card_bound_at'),
            last_updated_at=data.get('last_updated_at'),
            notes=data.get('notes'),
            created_at=data.get('created_at'),
        )


@dataclass
class AugmentLog:
    """Augment操作日志模型"""
    action_type: str  # register, bind_card, verify, extract_info
    status: str  # success, failed, processing
    message: str
    account_id: Optional[int] = None
    details: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'action_type': self.action_type,
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> 'AugmentLog':
        """从字典创建"""
        return AugmentLog(
            id=data.get('id'),
            account_id=data.get('account_id'),
            action_type=data['action_type'],
            status=data['status'],
            message=data['message'],
            details=data.get('details'),
            created_at=data.get('created_at'),
        )

