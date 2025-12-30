# -*- coding: utf-8 -*-
"""
数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Email:
    """邮箱模型"""
    id: Optional[int] = None
    email: str = ""
    type: str = "generated"  # generated | fixed
    status: str = "unused"  # unused | used | failed
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    used_at: Optional[str] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'type': self.type,
            'status': self.status,
            'created_at': self.created_at,
            'used_at': self.used_at
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            email=data.get('email', ''),
            type=data.get('type', 'generated'),
            status=data.get('status', 'unused'),
            created_at=data.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            used_at=data.get('used_at')
        )


@dataclass
class User:
    """用户信息模型"""
    id: Optional[int] = None
    full_name: str = ""  # 全名
    postal_code: str = ""  # 郵遞區號
    county: str = ""  # 縣
    district: str = ""  # 地區
    address_line1: str = ""  # 地址第 1 行
    address_line2: str = ""  # 地址第 2 行
    phone: str = ""  # 电话（可选）
    status: str = "unused"  # unused | used
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    used_at: Optional[str] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'postal_code': self.postal_code,
            'county': self.county,
            'district': self.district,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'phone': self.phone,
            'status': self.status,
            'created_at': self.created_at,
            'used_at': self.used_at
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            full_name=data.get('full_name', ''),
            postal_code=data.get('postal_code', ''),
            county=data.get('county', ''),
            district=data.get('district', ''),
            address_line1=data.get('address_line1', ''),
            address_line2=data.get('address_line2', ''),
            phone=data.get('phone', ''),
            status=data.get('status', 'unused'),
            created_at=data.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            used_at=data.get('used_at')
        )


@dataclass
class Card:
    """卡信息模型"""
    id: Optional[int] = None
    number: str = ""  # 卡号
    month: str = ""  # 过期月份
    year: str = ""  # 过期年份
    cvc: str = ""  # CVC
    card_type: str = "virtual"  # virtual | real
    status: str = "unused"  # unused | used | failed
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    used_at: Optional[str] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'number': self.number,
            'month': self.month,
            'year': self.year,
            'cvc': self.cvc,
            'card_type': self.card_type,
            'status': self.status,
            'created_at': self.created_at,
            'used_at': self.used_at
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            number=data.get('number', ''),
            month=data.get('month', ''),
            year=data.get('year', ''),
            cvc=data.get('cvc', ''),
            card_type=data.get('card_type', 'virtual'),
            status=data.get('status', 'unused'),
            created_at=data.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            used_at=data.get('used_at')
        )
    
    def get_masked_number(self):
        """获取脱敏卡号"""
        if len(self.number) >= 8:
            return f"{self.number[:4]} **** **** {self.number[-4:]}"
        return self.number


@dataclass
class Account:
    """已注册账号模型"""
    id: Optional[int] = None
    email: str = ""
    password: str = ""
    status: str = "registered"  # registered | failed | banned
    registered_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    last_login_at: Optional[str] = None
    notes: str = ""  # 备注
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'password': self.password,
            'status': self.status,
            'registered_at': self.registered_at,
            'last_login_at': self.last_login_at,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            email=data.get('email', ''),
            password=data.get('password', ''),
            status=data.get('status', 'registered'),
            registered_at=data.get('registered_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            last_login_at=data.get('last_login_at'),
            notes=data.get('notes', '')
        )

