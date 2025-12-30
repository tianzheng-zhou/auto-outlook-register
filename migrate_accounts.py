#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Outlook 账号迁移脚本
将 data/accounts.txt 中的数据迁移到 SQLite 数据库
"""
import sys
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from database.db_manager import DatabaseManager
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)


def load_accounts_from_file() -> List[Dict]:
    """从 txt 文件加载账号"""
    accounts = []
    
    try:
        if not Settings.ACCOUNTS_FILE.exists():
            logger.warning("账号文件不存在")
            return accounts
        
        with open(Settings.ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_account = {}
        for line in lines:
            line = line.strip()
            if line.startswith('状态:'):
                if current_account:
                    accounts.append(current_account)
                current_account = {'status': line.split(':', 1)[1].strip()}
            elif line.startswith('邮箱:'):
                current_account['email'] = line.split(':', 1)[1].strip()
            elif line.startswith('密码:'):
                current_account['password'] = line.split(':', 1)[1].strip()
            elif line.startswith('生日:'):
                current_account['birthday'] = line.split(':', 1)[1].strip()
            elif line.startswith('创建时间:'):
                current_account['created_at'] = line.split(':', 1)[1].strip()
            elif line.startswith('-' * 10):
                if current_account:
                    accounts.append(current_account)
                    current_account = {}
        
        # 添加最后一个账号
        if current_account:
            accounts.append(current_account)
        
        logger.info(f"从文件加载了 {len(accounts)} 个账号")
        return accounts
    except Exception as e:
        logger.error(f"加载账号失败: {e}")
        return []


def migrate_to_database(accounts: List[Dict]) -> int:
    """将账号迁移到数据库"""
    db_manager = DatabaseManager()
    success_count = 0
    skip_count = 0
    
    for account in accounts:
        try:
            email = account.get('email', '')
            password = account.get('password', '')
            birthday = account.get('birthday', '')
            status = account.get('status', 'unregistered')
            
            # 将"已注册"转换为"registered"，"未注册"转换为"unregistered"
            if status == '已注册':
                status = 'registered'
            elif status == '未注册':
                status = 'unregistered'
            
            # 检查是否已存在
            existing = db_manager.get_outlook_account_by_email(email)
            if existing:
                logger.warning(f"账号已存在，跳过: {email}")
                skip_count += 1
                continue
            
            # 添加到数据库
            db_manager.add_outlook_account(
                email=email,
                password=password,
                birthday=birthday,
                status=status
            )
            success_count += 1
            logger.info(f"✅ 迁移成功: {email}")
        
        except Exception as e:
            logger.error(f"❌ 迁移失败: {email} - {e}")
    
    return success_count, skip_count


def main():
    """主函数"""
    print("=" * 60)
    print("Outlook 账号迁移工具")
    print("=" * 60)
    
    # 加载文件中的账号
    print("\n📖 正在从文件加载账号...")
    accounts = load_accounts_from_file()
    
    if not accounts:
        print("❌ 没有找到任何账号")
        return
    
    print(f"✅ 加载了 {len(accounts)} 个账号")
    
    # 迁移到数据库
    print("\n💾 正在迁移到数据库...")
    success_count, skip_count = migrate_to_database(accounts)
    
    # 显示结果
    print("\n" + "=" * 60)
    print("迁移结果:")
    print(f"  成功: {success_count}")
    print(f"  跳过: {skip_count}")
    print(f"  总计: {len(accounts)}")
    print("=" * 60)
    
    if success_count > 0:
        print(f"\n✅ 成功迁移 {success_count} 个账号到数据库！")
    else:
        print("\n⚠️  没有新账号被迁移")


if __name__ == '__main__':
    main()

