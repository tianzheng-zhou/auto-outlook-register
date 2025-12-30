import sqlite3
import threading
import queue
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
from utils.logger import logger

class SQLiteHelper:
    def __init__(self, db_path, max_connections=5, row_as_dict=True):
        """
        初始化数据库连接池
        :param db_path: 数据库文件路径
        :param max_connections: 最大连接数
        :param row_as_dict: 查询结果是否返回 dict
        """
        self.db_path = str(db_path) if isinstance(db_path, Path) else db_path
        self.max_connections = max_connections
        self._pool = queue.Queue(max_connections)
        self._lock = threading.Lock()
        self._row_as_dict = row_as_dict
        self._closed = False
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.max_connections):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            if self._row_as_dict:
                conn.row_factory = sqlite3.Row
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            self._pool.put(conn)
        logger.info(f"✅ SQLite连接池初始化完成: {self.max_connections}个连接")

    def _get_conn(self):
        """从连接池获取连接"""
        if self._closed:
            raise RuntimeError("数据库连接池已关闭")
        return self._pool.get()

    def _release_conn(self, conn):
        """释放连接回连接池"""
        if not self._closed:
            self._pool.put(conn)

    @contextmanager
    def get_connection(self):
        """上下文管理器：获取数据库连接"""
        conn = self._get_conn()
        try:
            yield conn
        finally:
            self._release_conn(conn)

    def close(self):
        """关闭所有连接"""
        if self._closed:
            return

        self._closed = True
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except queue.Empty:
                break
        logger.info("✅ SQLite连接池已关闭")

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
        return False

    def execute(self, sql, params=None):
        """
        执行写操作（建表/插入/更新/删除等）
        :return: 影响的行数
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ SQLite执行错误: {e}, SQL: {sql}, 参数: {params}")
            raise
        finally:
            cursor.close()
            self._release_conn(conn)

    def executemany(self, sql, seq_of_params):
        """
        执行批量写操作
        :return: 影响的行数
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.executemany(sql, seq_of_params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ SQLite批量执行错误: {e}, SQL: {sql}")
            raise
        finally:
            cursor.close()
            self._release_conn(conn)

    def query(self, sql, params=None):
        """
        执行查询操作
        :return: list[dict] 或 list[tuple]
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            rows = cursor.fetchall()
            if self._row_as_dict:
                return [dict(row) for row in rows]
            else:
                return rows
        except Exception as e:
            logger.error(f"❌ SQLite查询错误: {e}, SQL: {sql}, 参数: {params}")
            raise
        finally:
            cursor.close()
            self._release_conn(conn)

    def query_one(self, sql, params=None):
        """
        执行查询操作，返回单条记录
        :return: dict 或 tuple 或 None
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            row = cursor.fetchone()
            if row and self._row_as_dict:
                return dict(row)
            return row
        except Exception as e:
            logger.error(f"❌ SQLite查询错误: {e}, SQL: {sql}, 参数: {params}")
            raise
        finally:
            cursor.close()
            self._release_conn(conn)

    def is_table_exist(self, table_name):
        """
        判断某表是否存在
        :param table_name: 表名
        :return: bool
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.query_one(sql, [table_name])
        return result is not None

    def get_last_insert_id(self):
        """
        获取最后插入的行ID
        :return: int
        """
        result = self.query_one("SELECT last_insert_rowid()")
        if result is None:
            return None

        # 如果返回的是字典（row_as_dict=True），获取第一个值
        if isinstance(result, dict):
            return list(result.values())[0]
        # 如果返回的是元组（row_as_dict=False），获取第一个元素
        else:
            return result[0]

    def transaction(self, operations):
        """
        批量事务操作（提供函数或 lambda 列表）
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            conn.execute("BEGIN")
            for op in operations:
                op(cursor)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"SQLite transaction error: {e}")
            raise
        finally:
            cursor.close()
            self._release_conn(conn)
