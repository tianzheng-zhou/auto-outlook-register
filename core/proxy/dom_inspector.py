# -*- coding: utf-8 -*-
"""
DOM检查和定位器生成工具
用于快速获取页面元素的定位器信息
"""
from selenium.webdriver.common.by import By
from utils.logger import get_logger

logger = get_logger(__name__)


class DOMInspector:
    """DOM检查工具"""
    
    @staticmethod
    def get_element_info(driver, element):
        """获取元素的详细信息"""
        try:
            info = {
                'tag': element.tag_name,
                'text': element.text.strip()[:100],
                'id': element.get_attribute('id'),
                'name': element.get_attribute('name'),
                'class': element.get_attribute('class'),
                'type': element.get_attribute('type'),
                'role': element.get_attribute('role'),
                'aria_label': element.get_attribute('aria-label'),
                'placeholder': element.get_attribute('placeholder'),
            }
            return info
        except Exception as e:
            logger.error(f"获取元素信息失败: {e}")
            return {}
    
    @staticmethod
    def find_elements_by_text(driver, text, tag='*'):
        """根据文本查找元素"""
        try:
            xpath = f"//{tag}[contains(text(), '{text}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            return elements
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return []
    
    @staticmethod
    def find_elements_by_aria_label(driver, aria_label):
        """根据aria-label查找元素"""
        try:
            xpath = f"//*[@aria-label='{aria_label}']"
            elements = driver.find_elements(By.XPATH, xpath)
            return elements
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return []
    
    @staticmethod
    def print_element_info(driver, element, label=""):
        """打印元素信息"""
        info = DOMInspector.get_element_info(driver, element)
        print(f"\n{'='*70}")
        if label:
            print(f"📍 {label}")
        print(f"{'='*70}")
        for key, value in info.items():
            if value:
                print(f"  {key:15}: {value}")
        print(f"{'='*70}\n")
    
    @staticmethod
    def dump_page_structure(driver, output_file=None):
        """导出页面结构到文件"""
        try:
            html = driver.page_source
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info(f"页面结构已导出到: {output_file}")
            else:
                return html
        except Exception as e:
            logger.error(f"导出页面结构失败: {e}")
            return None
    
    @staticmethod
    def find_dropdown_options(driver):
        """查找所有下拉菜单选项"""
        try:
            options = driver.find_elements(By.XPATH, "//div[@role='option']")
            option_texts = [opt.text.strip() for opt in options]
            print(f"\n📋 找到 {len(options)} 个下拉选项:")
            for i, text in enumerate(option_texts, 1):
                print(f"   {i}. {text}")
            return option_texts
        except Exception as e:
            logger.error(f"查找下拉选项失败: {e}")
            return []
    
    @staticmethod
    def find_all_buttons(driver):
        """查找所有按钮"""
        try:
            buttons = driver.find_elements(By.XPATH, "//button")
            print(f"\n🔘 找到 {len(buttons)} 个按钮:")
            for i, btn in enumerate(buttons[:20], 1):  # 只显示前20个
                text = btn.text.strip()[:50]
                btn_id = btn.get_attribute('id')
                btn_name = btn.get_attribute('name')
                print(f"   {i}. [{btn_id or btn_name or 'N/A'}] {text}")
            return buttons
        except Exception as e:
            logger.error(f"查找按钮失败: {e}")
            return []
    
    @staticmethod
    def find_all_inputs(driver):
        """查找所有输入框"""
        try:
            inputs = driver.find_elements(By.XPATH, "//input")
            print(f"\n📝 找到 {len(inputs)} 个输入框:")
            for i, inp in enumerate(inputs[:20], 1):  # 只显示前20个
                inp_id = inp.get_attribute('id')
                inp_name = inp.get_attribute('name')
                inp_type = inp.get_attribute('type')
                inp_placeholder = inp.get_attribute('placeholder')
                print(f"   {i}. [{inp_id or inp_name or 'N/A'}] type={inp_type} placeholder={inp_placeholder}")
            return inputs
        except Exception as e:
            logger.error(f"查找输入框失败: {e}")
            return []
    
    @staticmethod
    def generate_locators(element):
        """为元素生成多个定位器"""
        try:
            locators = []
            
            # ID定位器
            elem_id = element.get_attribute('id')
            if elem_id:
                locators.append((By.ID, elem_id))
            
            # Name定位器
            elem_name = element.get_attribute('name')
            if elem_name:
                locators.append((By.NAME, elem_name))
            
            # CSS选择器
            elem_class = element.get_attribute('class')
            if elem_class:
                locators.append((By.CSS_SELECTOR, f".{elem_class.split()[0]}"))
            
            # XPath定位器
            elem_text = element.text.strip()
            if elem_text:
                locators.append((By.XPATH, f"//*[contains(text(), '{elem_text[:30]}')]"))
            
            return locators
        except Exception as e:
            logger.error(f"生成定位器失败: {e}")
            return []


def inspect_page(driver):
    """交互式页面检查工具"""
    print("\n" + "="*70)
    print("🔍 DOM检查工具 - 交互式模式")
    print("="*70)
    print("命令列表:")
    print("  1. 查找所有按钮")
    print("  2. 查找所有输入框")
    print("  3. 查找下拉选项")
    print("  4. 导出页面结构")
    print("  5. 查找特定文本")
    print("  0. 退出")
    print("="*70)
    
    while True:
        try:
            cmd = input("\n请输入命令 (0-5): ").strip()
            
            if cmd == '0':
                break
            elif cmd == '1':
                DOMInspector.find_all_buttons(driver)
            elif cmd == '2':
                DOMInspector.find_all_inputs(driver)
            elif cmd == '3':
                DOMInspector.find_dropdown_options(driver)
            elif cmd == '4':
                output_file = input("输入输出文件路径 (默认: page_structure.html): ").strip()
                if not output_file:
                    output_file = "page_structure.html"
                DOMInspector.dump_page_structure(driver, output_file)
            elif cmd == '5':
                text = input("输入要查找的文本: ").strip()
                elements = DOMInspector.find_elements_by_text(driver, text)
                print(f"\n找到 {len(elements)} 个元素")
                for elem in elements[:5]:
                    DOMInspector.print_element_info(driver, elem)
            else:
                print("❌ 无效命令")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ 错误: {e}")

