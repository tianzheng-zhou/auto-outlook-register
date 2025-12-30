# -*- coding: utf-8 -*-
"""
虚拟卡生成器 - 使用Luhn算法生成合规的信用卡号
"""
import random
from typing import List
from database.models import Card


class CardGenerator:
    """虚拟卡生成器"""
    
    @staticmethod
    def luhn_checksum(card_number: str) -> int:
        """
        计算Luhn校验和
        :param card_number: 卡号（不含校验位）
        :return: 校验位
        """
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return (10 - (checksum % 10)) % 10
    
    @staticmethod
    def validate_card_number(card_number: str) -> bool:
        """
        验证卡号是否符合Luhn算法
        :param card_number: 完整卡号
        :return: bool
        """
        try:
            check_digit = int(card_number[-1])
            calculated_check = CardGenerator.luhn_checksum(card_number[:-1])
            return check_digit == calculated_check
        except (ValueError, IndexError):
            return False
    
    @staticmethod
    def generate_card_number(bin_value: str, length: int = 16) -> str:
        """
        根据BIN值生成完整卡号
        :param bin_value: BIN值（前6-8位）
        :param length: 卡号总长度（默认16位）
        :return: 完整卡号
        """
        # 确保BIN值是数字
        bin_value = ''.join(filter(str.isdigit, bin_value))
        
        if len(bin_value) > length - 1:
            raise ValueError(f"BIN值长度不能超过{length - 1}位")
        
        # 生成随机数字填充到length-1位（最后一位是校验位）
        remaining_length = length - len(bin_value) - 1
        random_digits = ''.join([str(random.randint(0, 9)) for _ in range(remaining_length)])
        
        # 组合BIN + 随机数字
        card_without_check = bin_value + random_digits
        
        # 计算校验位
        check_digit = CardGenerator.luhn_checksum(card_without_check)
        
        # 返回完整卡号
        return card_without_check + str(check_digit)
    
    @staticmethod
    def generate_expiration_date(month_option: str = "random", year_option: str = "random") -> tuple:
        """
        生成过期日期
        :param month_option: 月份选项（"random" 或 "01"-"12"）
        :param year_option: 年份选项（"random" 或 "2025"-"2035"）
        :return: (month, year)
        """
        # 生成月份
        if month_option == "random":
            month = str(random.randint(1, 12)).zfill(2)
        else:
            month = month_option.zfill(2)
        
        # 生成年份（未来2-8年）
        if year_option == "random":
            current_year = 2025
            year = str(random.randint(current_year + 2, current_year + 8))
        else:
            year = year_option
        
        return month, year
    
    @staticmethod
    def generate_cvv(length: int = 3) -> str:
        """
        生成CVV码
        :param length: CVV长度（3或4位）
        :return: CVV码
        """
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    @staticmethod
    def generate_cards(bin_value: str, 
                      count: int = 10,
                      card_length: int = 16,
                      month_option: str = "random",
                      year_option: str = "random",
                      cvv_option: str = "random") -> List[Card]:
        """
        批量生成虚拟卡
        :param bin_value: BIN值
        :param count: 生成数量
        :param card_length: 卡号长度
        :param month_option: 月份选项
        :param year_option: 年份选项
        :param cvv_option: CVV选项（"random" 或具体值）
        :return: Card对象列表
        """
        cards = []
        
        for _ in range(count):
            # 生成卡号
            card_number = CardGenerator.generate_card_number(bin_value, card_length)
            
            # 生成过期日期
            month, year = CardGenerator.generate_expiration_date(month_option, year_option)
            
            # 生成CVV
            if cvv_option == "random" or not cvv_option:
                # 根据卡号判断CVV长度（AmEx是4位，其他是3位）
                cvv_length = 4 if card_number.startswith('3') else 3
                cvv = CardGenerator.generate_cvv(cvv_length)
            else:
                cvv = cvv_option
            
            # 创建Card对象
            card = Card(
                number=card_number,
                month=month,
                year=year,
                cvc=cvv,
                card_type='virtual',
                status='unused'
            )
            cards.append(card)
        
        return cards
    
    @staticmethod
    def parse_card_string(card_string: str) -> List[Card]:
        """
        解析卡片字符串（格式：number|month|year|cvc）
        :param card_string: 卡片字符串（多行，每行一张卡）
        :return: Card对象列表
        """
        cards = []
        lines = card_string.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) >= 4:
                card = Card(
                    number=parts[0].strip(),
                    month=parts[1].strip(),
                    year=parts[2].strip(),
                    cvc=parts[3].strip(),
                    card_type='real',  # 手动输入的卡片标记为real
                    status='unused'
                )
                cards.append(card)
        
        return cards
    
    @staticmethod
    def format_card_to_string(card: Card) -> str:
        """
        将Card对象格式化为字符串
        :param card: Card对象
        :return: 格式化字符串（number|month|year|cvc）
        """
        return f"{card.number}|{card.month}|{card.year}|{card.cvc}"

