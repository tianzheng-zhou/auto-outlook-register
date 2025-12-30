# -*- coding: utf-8 -*-
"""
数据库表结构定义
"""

# 邮箱表
CREATE_EMAILS_TABLE = """
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL DEFAULT 'generated',
    status TEXT NOT NULL DEFAULT 'unused',
    created_at TEXT NOT NULL,
    used_at TEXT
);
"""

CREATE_EMAILS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_type ON emails(type);
"""

# 用户信息表
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    county TEXT NOT NULL,
    district TEXT NOT NULL,
    address_line1 TEXT NOT NULL,
    address_line2 TEXT,
    phone TEXT,
    status TEXT NOT NULL DEFAULT 'unused',
    created_at TEXT NOT NULL,
    used_at TEXT
);
"""

CREATE_USERS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
"""

# 卡信息表
CREATE_CARDS_TABLE = """
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL,
    month TEXT NOT NULL,
    year TEXT NOT NULL,
    cvc TEXT NOT NULL,
    card_type TEXT NOT NULL DEFAULT 'virtual',
    status TEXT NOT NULL DEFAULT 'unused',
    created_at TEXT NOT NULL,
    used_at TEXT
);
"""

CREATE_CARDS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(status);
CREATE INDEX IF NOT EXISTS idx_cards_type ON cards(card_type);
"""

# 已注册账号表
CREATE_ACCOUNTS_TABLE = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'registered',
    registered_at TEXT NOT NULL,
    last_login_at TEXT,
    notes TEXT
);
"""

CREATE_ACCOUNTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);
"""

# Outlook 账号表
CREATE_OUTLOOK_ACCOUNTS_TABLE = """
CREATE TABLE IF NOT EXISTS outlook_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    birthday TEXT,
    status TEXT NOT NULL DEFAULT 'unregistered',
    created_at TEXT NOT NULL,
    registered_at TEXT
);
"""

CREATE_OUTLOOK_ACCOUNTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_outlook_accounts_status ON outlook_accounts(status);
CREATE INDEX IF NOT EXISTS idx_outlook_accounts_email ON outlook_accounts(email);
"""

# 所有建表语句
ALL_CREATE_STATEMENTS = [
    CREATE_EMAILS_TABLE,
    CREATE_EMAILS_INDEX,
    CREATE_USERS_TABLE,
    CREATE_USERS_INDEX,
    CREATE_CARDS_TABLE,
    CREATE_CARDS_INDEX,
    CREATE_ACCOUNTS_TABLE,
    CREATE_ACCOUNTS_INDEX,
    CREATE_OUTLOOK_ACCOUNTS_TABLE,
    CREATE_OUTLOOK_ACCOUNTS_INDEX
]

