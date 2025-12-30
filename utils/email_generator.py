# -*- coding: utf-8 -*-
"""
邮箱生成器
"""
import random
import string
from typing import List
from database.models import Email


class EmailGenerator:
    """邮箱生成器"""
    
    @staticmethod
    def generate_emails_sequence(prefix: str, suffix: str, count: int, start_number: int = 1) -> List[Email]:
        """
        生成顺序邮箱（前缀 + 数字 + 后缀）
        :param prefix: 前缀
        :param suffix: 后缀（包含@domain.com）
        :param count: 生成数量
        :param start_number: 起始数字
        :return: Email对象列表
        """
        emails = []
        for i in range(count):
            email_address = f"{prefix}{start_number + i}{suffix}"
            email = Email(
                email=email_address,
                type='generated',
                status='unused'
            )
            emails.append(email)
        return emails
    
    @staticmethod
    def generate_emails_random(prefix: str, suffix: str, count: int, random_length: int = 6) -> List[Email]:
        """
        生成随机邮箱（前缀 + 随机字符串 + 后缀）
        :param prefix: 前缀
        :param suffix: 后缀（包含@domain.com）
        :param count: 生成数量
        :param random_length: 随机字符串长度
        :return: Email对象列表
        """
        emails = []
        for _ in range(count):
            # 生成随机字符串（小写字母+数字）
            random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random_length))
            email_address = f"{prefix}{random_str}{suffix}"
            email = Email(
                email=email_address,
                type='generated',
                status='unused'
            )
            emails.append(email)
        return emails
    
    @staticmethod
    def parse_fixed_emails(email_string: str) -> List[Email]:
        """
        解析固定邮箱列表（每行一个邮箱）
        :param email_string: 邮箱字符串（多行）
        :return: Email对象列表
        """
        emails = []
        lines = email_string.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 简单验证邮箱格式
            if '@' in line and '.' in line:
                email = Email(
                    email=line,
                    type='fixed',
                    status='unused'
                )
                emails.append(email)
        
        return emails

