"""
Augment账号注册系统的数据库管理器
"""

import json
from typing import List, Optional
from datetime import datetime

from utils.sqlite_helper import SQLiteHelper
from database.augment_schema import ALL_TABLES, AUGMENT_INDEXES
from database.augment_models import AugmentAccount, AugmentLog
from config.settings import Settings
from utils.logger import logger


class AugmentDBManager:
    """Augment数据库管理器（单例模式）"""
    
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            import threading
            cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db_path = Settings.DATABASE_PATH
        self.db = SQLiteHelper(str(self.db_path))
        self._init_database()
        self._initialized = True
        logger.info(f"AugmentDBManager initialized with database: {self.db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            # 创建所有表
            for table_sql in ALL_TABLES:
                self.db.execute(table_sql)

            # 创建索引
            for index_sql in AUGMENT_INDEXES:
                self.db.execute(index_sql)

            # 执行数据库迁移（添加新列等）
            self._migrate_database()

            logger.info("Augment database tables initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Augment database: {e}")
            raise

    def _migrate_database(self):
        """数据库迁移 - 添加新列等"""
        try:
            # 检查 proxies 表是否存在
            check_table = "SELECT name FROM sqlite_master WHERE type='table' AND name='proxies'"
            result = self.db.query(check_table)

            if result:
                # 检查 as_number 列是否存在
                check_column = "PRAGMA table_info(proxies)"
                columns = self.db.query(check_column)
                column_names = [col['name'] for col in columns]

                # 添加缺失的列
                if 'as_number' not in column_names:
                    logger.info("添加 as_number 列到 proxies 表...")
                    self.db.execute("ALTER TABLE proxies ADD COLUMN as_number TEXT")

                if 'provider' not in column_names:
                    logger.info("添加 provider 列到 proxies 表...")
                    self.db.execute("ALTER TABLE proxies ADD COLUMN provider TEXT")

                logger.info("✅ 数据库迁移完成")
        except Exception as e:
            logger.warning(f"⚠️ 数据库迁移失败（可能列已存在）: {e}")
    
    # ==================== Augment账号管理 ====================
    
    def add_account(self, account: AugmentAccount) -> int:
        """添加账号"""
        try:
            sql = """
                INSERT INTO augment_accounts (
                    email, password, tenant_url, auth_session, code, state,
                    portal_url, credits, total_credits, used_credits, plan_name,
                    next_billing_date, card_bound, card_number_masked, status,
                    registered_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                account.email, account.password, account.tenant_url, account.auth_session,
                account.code, account.state, account.portal_url, account.credits,
                account.total_credits, account.used_credits, account.plan_name,
                account.next_billing_date, account.card_bound, account.card_number_masked,
                account.status, account.registered_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                account.notes
            )
            self.db.execute(sql, params)
            account_id = self.db.get_last_insert_id()
            logger.info(f"Added Augment account: {account.email} (ID: {account_id})")
            return account_id
        except Exception as e:
            logger.error(f"Failed to add Augment account: {e}")
            raise
    
    def get_account_by_id(self, account_id: int) -> Optional[AugmentAccount]:
        """根据ID获取账号"""
        try:
            sql = "SELECT * FROM augment_accounts WHERE id = ?"
            row = self.db.query_one(sql, (account_id,))
            return AugmentAccount.from_dict(dict(row)) if row else None
        except Exception as e:
            logger.error(f"Failed to get Augment account by ID: {e}")
            return None
    
    def get_account_by_email(self, email: str) -> Optional[AugmentAccount]:
        """根据邮箱获取账号"""
        try:
            sql = "SELECT * FROM augment_accounts WHERE email = ?"
            row = self.db.query_one(sql, (email,))
            return AugmentAccount.from_dict(dict(row)) if row else None
        except Exception as e:
            logger.error(f"Failed to get Augment account by email: {e}")
            return None
    
    def get_all_accounts(self, status: Optional[str] = None) -> List[AugmentAccount]:
        """获取所有账号"""
        try:
            if status:
                sql = "SELECT * FROM augment_accounts WHERE status = ? ORDER BY created_at DESC"
                rows = self.db.query(sql, (status,))
            else:
                sql = "SELECT * FROM augment_accounts ORDER BY created_at DESC"
                rows = self.db.query(sql)
            return [AugmentAccount.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get all Augment accounts: {e}")
            return []
    
    def update_account(self, account_id: int, **kwargs) -> bool:
        """更新账号信息"""
        try:
            # 自动更新last_updated_at
            kwargs['last_updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            sql = f"UPDATE augment_accounts SET {set_clause} WHERE id = ?"
            params = tuple(kwargs.values()) + (account_id,)
            self.db.execute(sql, params)
            logger.info(f"Updated Augment account ID {account_id}: {kwargs}")
            return True
        except Exception as e:
            logger.error(f"Failed to update Augment account: {e}")
            return False
    
    def update_account_status(self, account_id: int, status: str, notes: Optional[str] = None) -> bool:
        """更新账号状态"""
        kwargs = {'status': status}
        if notes:
            kwargs['notes'] = notes
        return self.update_account(account_id, **kwargs)
    
    def bind_card_to_account(self, account_id: int, card_number_masked: str) -> bool:
        """绑卡到账号"""
        try:
            kwargs = {
                'card_bound': 1,
                'card_number_masked': card_number_masked,
                'card_bound_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'card_bound'
            }
            return self.update_account(account_id, **kwargs)
        except Exception as e:
            logger.error(f"Failed to bind card to account: {e}")
            return False
    
    def delete_account(self, account_id: int) -> bool:
        """删除账号"""
        try:
            sql = "DELETE FROM augment_accounts WHERE id = ?"
            self.db.execute(sql, (account_id,))
            logger.info(f"Deleted Augment account ID: {account_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Augment account: {e}")
            return False
    
    def get_account_count(self, status: Optional[str] = None) -> int:
        """获取账号数量"""
        try:
            if status:
                sql = "SELECT COUNT(*) as count FROM augment_accounts WHERE status = ?"
                row = self.db.query_one(sql, (status,))
            else:
                sql = "SELECT COUNT(*) as count FROM augment_accounts"
                row = self.db.query_one(sql)
            return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Failed to get Augment account count: {e}")
            return 0
    
    # ==================== 日志管理 ====================
    
    def add_log(self, log: AugmentLog) -> int:
        """添加日志"""
        try:
            sql = """
                INSERT INTO augment_logs (
                    account_id, action_type, status, message, details
                ) VALUES (?, ?, ?, ?, ?)
            """
            params = (
                log.account_id, log.action_type, log.status,
                log.message, log.details
            )
            self.db.execute(sql, params)
            log_id = self.db.get_last_insert_id()
            logger.debug(f"Added Augment log: {log.action_type} - {log.status}")
            return log_id
        except Exception as e:
            logger.error(f"Failed to add Augment log: {e}")
            raise
    
    def get_logs_by_account(self, account_id: int, limit: int = 100) -> List[AugmentLog]:
        """获取账号的日志"""
        try:
            sql = """
                SELECT * FROM augment_logs 
                WHERE account_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """
            rows = self.db.query(sql, (account_id, limit))
            return [AugmentLog.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get logs for account: {e}")
            return []
    
    def get_recent_logs(self, limit: int = 100) -> List[AugmentLog]:
        """获取最近的日志"""
        try:
            sql = "SELECT * FROM augment_logs ORDER BY created_at DESC LIMIT ?"
            rows = self.db.query(sql, (limit,))
            return [AugmentLog.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get recent logs: {e}")
            return []
    
    def clear_logs(self, account_id: Optional[int] = None) -> bool:
        """清空日志"""
        try:
            if account_id:
                sql = "DELETE FROM augment_logs WHERE account_id = ?"
                self.db.execute(sql, (account_id,))
                logger.info(f"Cleared logs for account ID: {account_id}")
            else:
                sql = "DELETE FROM augment_logs"
                self.db.execute(sql)
                logger.info("Cleared all Augment logs")
            return True
        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
            return False
    
    # ==================== 代理管理 ====================

    def add_proxy(self, protocol: str, host: str, port: int, username: str = None,
                  password: str = None, ip_address: str = None, location: str = None,
                  as_number: str = None, provider: str = None) -> int:
        """添加代理，如果已存在则更新"""
        try:
            # 构建代理URL
            if username and password:
                proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
            else:
                proxy_url = f"{protocol}://{host}:{port}"

            # 先检查代理是否已存在
            check_sql = "SELECT id FROM proxies WHERE proxy_url = ?"
            existing = self.db.query_one(check_sql, (proxy_url,))

            if existing:
                # 代理已存在，更新其信息
                proxy_id = existing['id']
                update_sql = """
                    UPDATE proxies
                    SET ip_address = ?, location = ?, as_number = ?, provider = ?,
                        is_valid = 1, last_checked = ?
                    WHERE id = ?
                """
                params = (
                    ip_address, location, as_number, provider,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'), proxy_id
                )
                self.db.execute(update_sql, params)
                logger.info(f"Updated existing proxy: {proxy_url} (ID: {proxy_id})")
                return proxy_id
            else:
                # 代理不存在，插入新记录
                insert_sql = """
                    INSERT INTO proxies (
                        protocol, host, port, username, password, proxy_url,
                        ip_address, location, as_number, provider, is_valid, last_checked
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    protocol, host, port, username, password, proxy_url,
                    ip_address, location, as_number, provider, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )

                # 在同一个连接上执行 INSERT 和 SELECT，确保获取正确的 ID
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(insert_sql, params)
                    cursor.execute("SELECT last_insert_rowid()")
                    proxy_id = cursor.fetchone()[0]
                    conn.commit()

                logger.info(f"Added new proxy: {proxy_url} (ID: {proxy_id})")
                return proxy_id
        except Exception as e:
            logger.error(f"Failed to add proxy: {e}")
            raise

    def get_all_proxies(self) -> List[dict]:
        """获取所有代理"""
        try:
            sql = "SELECT * FROM proxies ORDER BY created_at DESC"
            rows = self.db.query(sql)
            return rows if isinstance(rows, list) and rows and isinstance(rows[0], dict) else [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get proxies: {e}")
            return []

    def get_proxy_by_id(self, proxy_id: int) -> Optional[dict]:
        """根据ID获取代理"""
        try:
            sql = "SELECT * FROM proxies WHERE id = ?"
            row = self.db.query_one(sql, (proxy_id,))
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get proxy by ID: {e}")
            return None

    def update_proxy_info(self, proxy_id: int, ip_address: str, location: str,
                         as_number: str = None, provider: str = None) -> bool:
        """更新代理信息（IP、位置、AS号码、商家）"""
        try:
            sql = """
                UPDATE proxies
                SET ip_address = ?, location = ?, as_number = ?, provider = ?,
                    last_checked = ?, is_valid = 1
                WHERE id = ?
            """
            params = (ip_address, location, as_number, provider,
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S'), proxy_id)
            self.db.execute(sql, params)
            logger.info(f"Updated proxy {proxy_id}: IP={ip_address}, Location={location}, AS={as_number}, Provider={provider}")
            return True
        except Exception as e:
            logger.error(f"Failed to update proxy info: {e}")
            return False

    def delete_proxy(self, proxy_id: int) -> bool:
        """删除代理"""
        try:
            sql = "DELETE FROM proxies WHERE id = ?"
            self.db.execute(sql, (proxy_id,))
            logger.info(f"Deleted proxy: {proxy_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete proxy: {e}")
            return False

    def clear_proxies(self) -> bool:
        """清空所有代理"""
        try:
            sql = "DELETE FROM proxies"
            self.db.execute(sql)
            logger.info("Cleared all proxies")
            return True
        except Exception as e:
            logger.error(f"Failed to clear proxies: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'db'):
            self.db.close()
            logger.info("AugmentDBManager closed")

