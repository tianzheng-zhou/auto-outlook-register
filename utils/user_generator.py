# -*- coding: utf-8 -*-
"""
用户信息生成器
"""
import random
from typing import List
from database.models import User


class UserGenerator:
    """用户信息生成器"""
    
    # 常用姓氏
    LAST_NAMES = [
        '王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴',
        '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '罗', '高'
    ]
    
    # 常用名字
    FIRST_NAMES = [
        '伟', '芳', '娜', '秀英', '敏', '静', '丽', '强', '磊', '军',
        '洋', '勇', '艳', '杰', '涛', '明', '超', '秀兰', '霞', '平'
    ]
    
    # 台湾常用姓名
    TW_LAST_NAMES = ['陳', '林', '黃', '張', '李', '王', '吳', '劉', '蔡', '楊']
    TW_FIRST_NAMES = ['思敏', '雅婷', '怡君', '淑芬', '美玲', '志明', '建宏', '俊傑', '家豪', '冠宇']
    
    # 台湾县市
    TW_COUNTIES = ['台北市', '新北市', '桃園市', '台中市', '台南市', '高雄市', '基隆市', '新竹市', '嘉義市']
    
    # 台湾地区（按县市）
    TW_DISTRICTS = {
        '台北市': ['中正區', '大同區', '中山區', '松山區', '大安區', '萬華區', '信義區', '士林區', '北投區', '內湖區', '南港區', '文山區'],
        '新北市': ['板橋區', '三重區', '中和區', '永和區', '新莊區', '新店區', '樹林區', '鶯歌區', '三峽區', '淡水區', '汐止區', '瑞芳區'],
        '桃園市': ['桃園區', '中壢區', '平鎮區', '八德區', '楊梅區', '蘆竹區', '大溪區', '龍潭區', '龜山區', '大園區', '觀音區', '新屋區'],
        '台中市': ['中區', '東區', '南區', '西區', '北區', '北屯區', '西屯區', '南屯區', '太平區', '大里區', '霧峰區', '烏日區'],
        '台南市': ['中西區', '東區', '南區', '北區', '安平區', '安南區', '永康區', '歸仁區', '新化區', '左鎮區', '玉井區', '楠西區'],
        '高雄市': ['新興區', '前金區', '苓雅區', '鹽埕區', '鼓山區', '旗津區', '前鎮區', '三民區', '楠梓區', '小港區', '左營區', '仁武區'],
        '基隆市': ['仁愛區', '信義區', '中正區', '中山區', '安樂區', '暖暖區', '七堵區'],
        '新竹市': ['東區', '北區', '香山區'],
        '嘉義市': ['東區', '西區']
    }
    
    # 台湾街道名称
    TW_STREETS = [
        '中山路', '中正路', '民生路', '民權路', '忠孝路', '信義路', '和平路', '仁愛路',
        '光復路', '建國路', '中華路', '復興路', '博愛路', '自由路', '三民路', '四維路'
    ]
    
    @staticmethod
    def generate_random_name(use_taiwan: bool = True) -> str:
        """
        生成随机姓名
        :param use_taiwan: 是否使用台湾姓名
        :return: 姓名
        """
        if use_taiwan:
            last_name = random.choice(UserGenerator.TW_LAST_NAMES)
            first_name = random.choice(UserGenerator.TW_FIRST_NAMES)
        else:
            last_name = random.choice(UserGenerator.LAST_NAMES)
            first_name = random.choice(UserGenerator.FIRST_NAMES)
        
        return last_name + first_name
    
    @staticmethod
    def generate_random_address(county: str = None) -> tuple:
        """
        生成随机地址
        :param county: 指定县市（如果为None则随机）
        :return: (postal_code, county, district, address_line1)
        """
        # 选择县市
        if county is None or county not in UserGenerator.TW_COUNTIES:
            county = random.choice(UserGenerator.TW_COUNTIES)
        
        # 选择地区
        district = random.choice(UserGenerator.TW_DISTRICTS.get(county, ['中正區']))
        
        # 生成邮递区号（100-999）
        postal_code = str(random.randint(100, 999))
        
        # 生成街道地址
        street = random.choice(UserGenerator.TW_STREETS)
        number = random.randint(1, 999)
        address_line1 = f"{street}{number}號"
        
        return postal_code, county, district, address_line1
    
    @staticmethod
    def generate_random_phone() -> str:
        """
        生成随机台湾手机号
        :return: 手机号
        """
        # 台湾手机号格式：09XX-XXX-XXX
        prefix = '09'
        middle = str(random.randint(10, 99))
        part1 = str(random.randint(100, 999))
        part2 = str(random.randint(100, 999))
        return f"{prefix}{middle}-{part1}-{part2}"
    
    @staticmethod
    def generate_users(count: int, use_taiwan: bool = True) -> List[User]:
        """
        批量生成随机用户
        :param count: 生成数量
        :param use_taiwan: 是否使用台湾地址
        :return: User对象列表
        """
        users = []
        
        for _ in range(count):
            # 生成姓名
            full_name = UserGenerator.generate_random_name(use_taiwan)
            
            # 生成地址
            postal_code, county, district, address_line1 = UserGenerator.generate_random_address()
            
            # 生成电话（50%概率）
            phone = UserGenerator.generate_random_phone() if random.random() > 0.5 else ""
            
            # 创建User对象
            user = User(
                full_name=full_name,
                postal_code=postal_code,
                county=county,
                district=district,
                address_line1=address_line1,
                address_line2="",  # 地址第2行默认为空
                phone=phone,
                status='unused'
            )
            users.append(user)
        
        return users
    
    @staticmethod
    def parse_user_string(user_string: str) -> List[User]:
        """
        解析用户信息字符串
        格式：
        全名：劉思敏
        郵遞區號：110
        縣：台北市
        地區：信義區
        地址第 1 行：市府路7號
        地址第 2 行：（選填）
        
        :param user_string: 用户信息字符串（多个用户用空行分隔）
        :return: User对象列表
        """
        users = []
        lines = user_string.strip().split('\n')
        
        current_user_data = {}
        
        for line in lines:
            line = line.strip()
            
            # 空行表示一个用户结束
            if not line:
                if current_user_data:
                    user = User(
                        full_name=current_user_data.get('全名', ''),
                        postal_code=current_user_data.get('郵遞區號', ''),
                        county=current_user_data.get('縣', ''),
                        district=current_user_data.get('地區', ''),
                        address_line1=current_user_data.get('地址第 1 行', ''),
                        address_line2=current_user_data.get('地址第 2 行', ''),
                        phone=current_user_data.get('電話', ''),
                        status='unused'
                    )
                    users.append(user)
                    current_user_data = {}
                continue
            
            # 解析键值对
            if '：' in line or ':' in line:
                separator = '：' if '：' in line else ':'
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    
                    # 跳过"（選填）"等提示
                    if value and not value.startswith('（'):
                        current_user_data[key] = value
        
        # 处理最后一个用户
        if current_user_data:
            user = User(
                full_name=current_user_data.get('全名', ''),
                postal_code=current_user_data.get('郵遞區號', ''),
                county=current_user_data.get('縣', ''),
                district=current_user_data.get('地區', ''),
                address_line1=current_user_data.get('地址第 1 行', ''),
                address_line2=current_user_data.get('地址第 2 行', ''),
                phone=current_user_data.get('電話', ''),
                status='unused'
            )
            users.append(user)
        
        return users

