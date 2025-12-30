# -*- coding: utf-8 -*-
"""
数据库管理器
"""
import sys
from pathlib import Path
from typing import List, Optional
from utils.sqlite_helper import SQLiteHelper
from utils.logger import logger
from .models import Email, User, Card, Account
from .schema import ALL_CREATE_STATEMENTS


class DatabaseManager:
    """数据库管理器"""

    _instance = None
    _lock = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            import threading
            if cls._lock is None:
                cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化数据库管理器
        :param db_path: 数据库文件路径，如果为None则使用默认路径
        """
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 确定数据库路径
        if db_path is None:
            db_path = self._get_default_db_path()

        self.db_path = Path(db_path)

        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化SQLite Helper
        self.db = SQLiteHelper(str(self.db_path), max_connections=5, row_as_dict=True)

        # 初始化数据库表
        self._init_tables()

        self._initialized = True
        logger.info(f"✅ 数据库管理器初始化完成: {self.db_path}")

    def _get_default_db_path(self) -> Path:
        """
        获取默认数据库路径
        开发环境：项目根目录/data/outlook.db
        打包后：用户数据目录/outlook.db
        """
        if getattr(sys, 'frozen', False):
            # 打包后：使用用户数据目录
            import platform
            system = platform.system()

            if system == "Darwin":  # macOS
                base_dir = Path.home() / "Library" / "Application Support" / "OutlookRegister"
            elif system == "Windows":
                import os
                base_dir = Path(os.getenv('APPDATA', Path.home())) / "OutlookRegister"
            else:  # Linux
                base_dir = Path.home() / ".config" / "OutlookRegister"

            base_dir.mkdir(parents=True, exist_ok=True)
            return base_dir / "outlook.db"
        else:
            # 开发环境：项目根目录/data/outlook.db
            project_root = Path(__file__).resolve().parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir / "outlook.db"

    def _init_tables(self):
        """初始化数据库表"""
        try:
            for statement in ALL_CREATE_STATEMENTS:
                # 分割多条SQL语句
                statements = [s.strip() for s in statement.split(';') if s.strip()]
                for sql in statements:
                    self.db.execute(sql)
            logger.info("✅ 数据库表初始化完成")
        except Exception as e:
            logger.error(f"❌ 数据库表初始化失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'db'):
            self.db.close()

    # ==================== 邮箱管理 ====================

    def add_email(self, email: Email) -> int:
        """添加邮箱"""
        sql = """
        INSERT INTO emails (email, type, status, created_at)
        VALUES (?, ?, ?, ?)
        """
        try:
            self.db.execute(sql, [email.email, email.type, email.status, email.created_at])
            return self.db.get_last_insert_id()
        except Exception as e:
            logger.error(f"❌ 添加邮箱失败: {e}")
            raise

    def add_emails_batch(self, emails: List[Email]) -> int:
        """批量添加邮箱"""
        sql = """
        INSERT INTO emails (email, type, status, created_at)
        VALUES (?, ?, ?, ?)
        """
        params = [[e.email, e.type, e.status, e.created_at] for e in emails]
        try:
            return self.db.executemany(sql, params)
        except Exception as e:
            logger.error(f"❌ 批量添加邮箱失败: {e}")
            raise

    def get_email_by_id(self, email_id: int) -> Optional[Email]:
        """根据ID获取邮箱"""
        sql = "SELECT * FROM emails WHERE id = ?"
        result = self.db.query_one(sql, [email_id])
        return Email.from_dict(result) if result else None

    def get_all_emails(self, status: Optional[str] = None) -> List[Email]:
        """获取所有邮箱"""
        if status:
            sql = "SELECT * FROM emails WHERE status = ? ORDER BY created_at DESC"
            results = self.db.query(sql, [status])
        else:
            sql = "SELECT * FROM emails ORDER BY created_at DESC"
            results = self.db.query(sql)
        return [Email.from_dict(r) for r in results]

    def get_unused_email(self) -> Optional[Email]:
        """获取一个未使用的邮箱"""
        sql = "SELECT * FROM emails WHERE status = 'unused' ORDER BY created_at ASC LIMIT 1"
        result = self.db.query_one(sql)
        return Email.from_dict(result) if result else None

    def update_email_status(self, email_id: int, status: str, used_at: Optional[str] = None):
        """更新邮箱状态"""
        if used_at:
            sql = "UPDATE emails SET status = ?, used_at = ? WHERE id = ?"
            self.db.execute(sql, [status, used_at, email_id])
        else:
            sql = "UPDATE emails SET status = ? WHERE id = ?"
            self.db.execute(sql, [status, email_id])

    def delete_email(self, email_id: int):
        """删除邮箱"""
        sql = "DELETE FROM emails WHERE id = ?"
        self.db.execute(sql, [email_id])

    def get_email_count(self, status: Optional[str] = None) -> int:
        """获取邮箱数量"""
        if status:
            sql = "SELECT COUNT(*) as count FROM emails WHERE status = ?"
            result = self.db.query_one(sql, [status])
        else:
            sql = "SELECT COUNT(*) as count FROM emails"
            result = self.db.query_one(sql)
        return result['count'] if result else 0

    # ==================== 用户管理 ====================

    def add_user(self, user: User) -> int:
        """添加用户"""
        sql = """
        INSERT INTO users (full_name, postal_code, county, district, address_line1, address_line2, phone, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            self.db.execute(sql, [
                user.full_name, user.postal_code, user.county, user.district,
                user.address_line1, user.address_line2, user.phone, user.status, user.created_at
            ])
            return self.db.get_last_insert_id()
        except Exception as e:
            logger.error(f"❌ 添加用户失败: {e}")
            raise

    def add_users_batch(self, users: List[User]) -> int:
        """批量添加用户"""
        sql = """
        INSERT INTO users (full_name, postal_code, county, district, address_line1, address_line2, phone, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [[
            u.full_name, u.postal_code, u.county, u.district,
            u.address_line1, u.address_line2, u.phone, u.status, u.created_at
        ] for u in users]
        try:
            return self.db.executemany(sql, params)
        except Exception as e:
            logger.error(f"❌ 批量添加用户失败: {e}")
            raise

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        sql = "SELECT * FROM users WHERE id = ?"
        result = self.db.query_one(sql, [user_id])
        return User.from_dict(result) if result else None

    def get_all_users(self, status: Optional[str] = None) -> List[User]:
        """获取所有用户"""
        if status:
            sql = "SELECT * FROM users WHERE status = ? ORDER BY created_at DESC"
            results = self.db.query(sql, [status])
        else:
            sql = "SELECT * FROM users ORDER BY created_at DESC"
            results = self.db.query(sql)
        return [User.from_dict(r) for r in results]

    def get_random_user(self) -> Optional[User]:
        """随机获取一个未使用的用户"""
        sql = "SELECT * FROM users WHERE status = 'unused' ORDER BY RANDOM() LIMIT 1"
        result = self.db.query_one(sql)
        return User.from_dict(result) if result else None

    def update_user_status(self, user_id: int, status: str, used_at: Optional[str] = None):
        """更新用户状态"""
        if used_at:
            sql = "UPDATE users SET status = ?, used_at = ? WHERE id = ?"
            self.db.execute(sql, [status, used_at, user_id])
        else:
            sql = "UPDATE users SET status = ? WHERE id = ?"
            self.db.execute(sql, [status, user_id])

    def delete_user(self, user_id: int):
        """删除用户"""
        sql = "DELETE FROM users WHERE id = ?"
        self.db.execute(sql, [user_id])

    def get_user_count(self, status: Optional[str] = None) -> int:
        """获取用户数量"""
        if status:
            sql = "SELECT COUNT(*) as count FROM users WHERE status = ?"
            result = self.db.query_one(sql, [status])
        else:
            sql = "SELECT COUNT(*) as count FROM users"
            result = self.db.query_one(sql)
        return result['count'] if result else 0

    # ==================== 卡片管理 ====================

    def add_card(self, card: Card) -> int:
        """添加卡片"""
        sql = """
        INSERT INTO cards (number, month, year, cvc, card_type, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        try:
            self.db.execute(sql, [
                card.number, card.month, card.year, card.cvc,
                card.card_type, card.status, card.created_at
            ])
            return self.db.get_last_insert_id()
        except Exception as e:
            logger.error(f"❌ 添加卡片失败: {e}")
            raise

    def add_cards_batch(self, cards: List[Card]) -> int:
        """批量添加卡片"""
        sql = """
        INSERT INTO cards (number, month, year, cvc, card_type, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = [[
            c.number, c.month, c.year, c.cvc,
            c.card_type, c.status, c.created_at
        ] for c in cards]
        try:
            return self.db.executemany(sql, params)
        except Exception as e:
            logger.error(f"❌ 批量添加卡片失败: {e}")
            raise

    def get_card_by_id(self, card_id: int) -> Optional[Card]:
        """根据ID获取卡片"""
        sql = "SELECT * FROM cards WHERE id = ?"
        result = self.db.query_one(sql, [card_id])
        return Card.from_dict(result) if result else None

    def get_all_cards(self, status: Optional[str] = None) -> List[Card]:
        """获取所有卡片"""
        if status:
            sql = "SELECT * FROM cards WHERE status = ? ORDER BY created_at DESC"
            results = self.db.query(sql, [status])
        else:
            sql = "SELECT * FROM cards ORDER BY created_at DESC"
            results = self.db.query(sql)
        return [Card.from_dict(r) for r in results]

    def get_unused_card(self) -> Optional[Card]:
        """获取第一个未使用的卡片（按创建时间顺序）"""
        sql = "SELECT * FROM cards WHERE status = 'unused' ORDER BY created_at ASC LIMIT 1"
        result = self.db.query_one(sql)
        return Card.from_dict(result) if result else None

    def get_random_card(self) -> Optional[Card]:
        """随机获取一个未使用的卡片"""
        sql = "SELECT * FROM cards WHERE status = 'unused' ORDER BY RANDOM() LIMIT 1"
        result = self.db.query_one(sql)
        return Card.from_dict(result) if result else None

    def update_card_status(self, card_id: int, status: str, used_at: Optional[str] = None):
        """更新卡片状态"""
        if used_at:
            sql = "UPDATE cards SET status = ?, used_at = ? WHERE id = ?"
            self.db.execute(sql, [status, used_at, card_id])
        else:
            sql = "UPDATE cards SET status = ? WHERE id = ?"
            self.db.execute(sql, [status, card_id])

    def delete_card(self, card_id: int):
        """删除卡片"""
        sql = "DELETE FROM cards WHERE id = ?"
        self.db.execute(sql, [card_id])

    def get_card_count(self, status: Optional[str] = None) -> int:
        """获取卡片数量"""
        if status:
            sql = "SELECT COUNT(*) as count FROM cards WHERE status = ?"
            result = self.db.query_one(sql, [status])
        else:
            sql = "SELECT COUNT(*) as count FROM cards"
            result = self.db.query_one(sql)
        return result['count'] if result else 0

    # ==================== 账号管理 ====================

    def add_account(self, account: Account) -> int:
        """添加已注册账号"""
        sql = """
        INSERT INTO accounts (email, password, status, registered_at, notes)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            self.db.execute(sql, [
                account.email, account.password, account.status,
                account.registered_at, account.notes
            ])
            return self.db.get_last_insert_id()
        except Exception as e:
            logger.error(f"❌ 添加账号失败: {e}")
            raise

    def get_account_by_email(self, email: str) -> Optional[Account]:
        """根据邮箱获取账号"""
        sql = "SELECT * FROM accounts WHERE email = ?"
        result = self.db.query_one(sql, [email])
        return Account.from_dict(result) if result else None

    def get_all_accounts(self, status: Optional[str] = None) -> List[Account]:
        """获取所有账号"""
        if status:
            sql = "SELECT * FROM accounts WHERE status = ? ORDER BY registered_at DESC"
            results = self.db.query(sql, [status])
        else:
            sql = "SELECT * FROM accounts ORDER BY registered_at DESC"
            results = self.db.query(sql)
        return [Account.from_dict(r) for r in results]

    def update_account_status(self, account_id: int, status: str):
        """更新账号状态"""
        sql = "UPDATE accounts SET status = ? WHERE id = ?"
        self.db.execute(sql, [status, account_id])

    def update_account_last_login(self, account_id: int, last_login_at: str):
        """更新账号最后登录时间"""
        sql = "UPDATE accounts SET last_login_at = ? WHERE id = ?"
        self.db.execute(sql, [last_login_at, account_id])

    def delete_account(self, account_id: int):
        """删除账号"""
        sql = "DELETE FROM accounts WHERE id = ?"
        self.db.execute(sql, [account_id])

    def get_account_count(self, status: Optional[str] = None) -> int:
        """获取账号数量"""
        if status:
            sql = "SELECT COUNT(*) as count FROM accounts WHERE status = ?"
            result = self.db.query_one(sql, [status])
        else:
            sql = "SELECT COUNT(*) as count FROM accounts"
            result = self.db.query_one(sql)
        return result['count'] if result else 0

    # ==================== Outlook 账号管理 ====================

    def add_outlook_account(self, email: str, password: str, birthday: Optional[str] = None,
                           status: str = "unregistered") -> int:
        """添加 Outlook 账号"""
        import time
        sql = """
        INSERT INTO outlook_accounts (email, password, birthday, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            created_at = time.strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute(sql, [email, password, birthday, status, created_at])
            return self.db.get_last_insert_id()
        except Exception as e:
            logger.error(f"❌ 添加 Outlook 账号失败: {e}")
            raise

    def get_outlook_account_by_email(self, email: str) -> Optional[dict]:
        """根据邮箱获取 Outlook 账号"""
        sql = "SELECT * FROM outlook_accounts WHERE email = ?"
        return self.db.query_one(sql, [email])

    def get_all_outlook_accounts(self, status: Optional[str] = None) -> List[dict]:
        """获取所有 Outlook 账号"""
        if status:
            sql = "SELECT * FROM outlook_accounts WHERE status = ? ORDER BY created_at DESC"
            results = self.db.query(sql, [status])
        else:
            sql = "SELECT * FROM outlook_accounts ORDER BY created_at DESC"
            results = self.db.query(sql)
        return results if results else []

    def update_outlook_account_status(self, email: str, status: str, registered_at: Optional[str] = None):
        """更新 Outlook 账号状态"""
        if registered_at:
            sql = "UPDATE outlook_accounts SET status = ?, registered_at = ? WHERE email = ?"
            self.db.execute(sql, [status, registered_at, email])
        else:
            sql = "UPDATE outlook_accounts SET status = ? WHERE email = ?"
            self.db.execute(sql, [status, email])

    def delete_outlook_account(self, email: str):
        """删除 Outlook 账号"""
        sql = "DELETE FROM outlook_accounts WHERE email = ?"
        self.db.execute(sql, [email])

    def get_outlook_account_count(self, status: Optional[str] = None) -> int:
        """获取 Outlook 账号数量"""
        if status:
            sql = "SELECT COUNT(*) as count FROM outlook_accounts WHERE status = ?"
            result = self.db.query_one(sql, [status])
        else:
            sql = "SELECT COUNT(*) as count FROM outlook_accounts"
            result = self.db.query_one(sql)
        return result['count'] if result else 0


