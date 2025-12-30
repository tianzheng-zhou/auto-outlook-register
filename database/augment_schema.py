"""
Augment账号注册系统的数据库表结构

表设计：
1. augment_accounts - Augment账号信息
2. augment_logs - 注册和绑卡日志
"""

# Augment账号表
AUGMENT_ACCOUNTS_TABLE = """
CREATE TABLE IF NOT EXISTS augment_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT,
    tenant_url TEXT,
    auth_session TEXT,
    code TEXT,
    state TEXT,
    portal_url TEXT,
    credits INTEGER DEFAULT 0,
    total_credits INTEGER DEFAULT 30000,
    used_credits INTEGER DEFAULT 0,
    plan_name TEXT DEFAULT 'Free Plan',
    next_billing_date TEXT,
    card_bound INTEGER DEFAULT 0,
    card_number_masked TEXT,
    status TEXT DEFAULT 'registered',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    card_bound_at TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Augment操作日志表
AUGMENT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS augment_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES augment_accounts(id) ON DELETE CASCADE
);
"""

# 代理表
PROXY_TABLE = """
CREATE TABLE IF NOT EXISTS proxies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    username TEXT,
    password TEXT,
    proxy_url TEXT NOT NULL UNIQUE,
    ip_address TEXT,
    location TEXT,
    as_number TEXT,
    provider TEXT,
    is_valid INTEGER DEFAULT 1,
    last_checked TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 索引
AUGMENT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_augment_accounts_email ON augment_accounts(email);",
    "CREATE INDEX IF NOT EXISTS idx_augment_accounts_status ON augment_accounts(status);",
    "CREATE INDEX IF NOT EXISTS idx_augment_accounts_card_bound ON augment_accounts(card_bound);",
    "CREATE INDEX IF NOT EXISTS idx_augment_logs_account_id ON augment_logs(account_id);",
    "CREATE INDEX IF NOT EXISTS idx_augment_logs_action_type ON augment_logs(action_type);",
    "CREATE INDEX IF NOT EXISTS idx_proxies_proxy_url ON proxies(proxy_url);",
    "CREATE INDEX IF NOT EXISTS idx_proxies_is_valid ON proxies(is_valid);",
]

# 所有表
ALL_TABLES = [
    AUGMENT_ACCOUNTS_TABLE,
    AUGMENT_LOGS_TABLE,
    PROXY_TABLE,
]

