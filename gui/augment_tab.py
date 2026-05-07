"""
Augment注册管理Tab - 完整功能版本
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QTextEdit, QMessageBox, QHeaderView, QGroupBox, QSplitter,
    QDialog, QPlainTextEdit, QProgressDialog, QRadioButton,
    QCheckBox, QLineEdit, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QColor, QIcon

from database.augment_db_manager import AugmentDBManager
from database.db_manager import DatabaseManager
from core.register.register_factory import RegisterFactory
from core.register.base_register import BaseRegister
from core.proxy import create_stealth_browser, get_proxy_manager, ProxyDetector
from core.proxy.proxy_manager import ProxyConfig
from config.settings import Settings
from config.proxy_chain_settings import (
    load_chain_settings, save_chain_settings, DEFAULT_UPSTREAM_URL,
)
from utils.logger import logger


class RegisterWorker(QThread):
    """注册工作线程"""
    progress = pyqtSignal(str, str)  # level, message
    finished = pyqtSignal(bool, str)  # 成功/失败, 消息

    def __init__(self, email: str, user_info: dict):
        super().__init__()
        self.email = email
        self.user_info = user_info
        self.register: Optional[BaseRegister] = None
        self.driver = None  # 保存 driver 引用，便于在 finally 中清理链式代理 server
        self.is_running = True

    def run(self):
        try:
            self.progress.emit("info", "🔄 正在获取代理...")
            # 获取代理
            proxy_manager = get_proxy_manager()
            proxy = proxy_manager.get_next_proxy()

            if proxy:
                self.progress.emit("info", f"✅ 获取代理: {proxy.to_chrome_proxy()}")
            else:
                self.progress.emit("warning", "⚠️ 未配置代理，使用本地IP")

            # 读取链式代理（上游 / 系统代理）配置
            upstream_proxy = None
            if proxy:
                try:
                    chain_settings = load_chain_settings()
                    if chain_settings.get("enabled"):
                        upstream_url = chain_settings.get("upstream_url") or DEFAULT_UPSTREAM_URL
                        upstream_proxy = proxy_manager._parse_proxy_string(upstream_url)
                        self.progress.emit(
                            "info",
                            f"🔗 启用链式代理：先走上游 {upstream_proxy.host}:{upstream_proxy.port}",
                        )
                except Exception as e:
                    self.progress.emit("warning", f"⚠️ 解析上游代理失败，将忽略: {e}")
                    upstream_proxy = None

            self.progress.emit("info", "🌐 正在创建浏览器...")
            # 创建浏览器
            self.driver = create_stealth_browser(
                chrome_version=Settings.CHROME_VERSION,
                headless=False,
                proxy=proxy,
                upstream_proxy=upstream_proxy,
            )

            self.progress.emit("info", "✅ 浏览器创建成功")

            self.progress.emit("info", "🔧 正在创建注册器...")
            # 创建注册器
            self.register = RegisterFactory.create_register('augment', self.driver)

            # 设置日志回调（接收level和message两个参数）
            self.register.set_log_callback(self.progress.emit)

            self.progress.emit("info", "🚀 开始注册流程...")
            # 开始注册
            success = self.register.start_register(self.email, self.user_info)

            if success:
                self.finished.emit(True, "注册成功")
            else:
                self.finished.emit(False, "注册失败")

        except Exception as e:
            import traceback
            logger.error(f"注册线程错误: {e}")
            logger.error(traceback.format_exc())
            self.progress.emit("error", f"❌ 错误: {str(e)}")
            self.finished.emit(False, str(e))
        finally:
            self._cleanup_chain_server()

    def stop(self):
        """停止注册"""
        self.is_running = False
        if self.register:
            self.register.stop()
        self._cleanup_chain_server()

    def _cleanup_chain_server(self):
        """关闭浏览器后，停掉本地链式代理 server，释放端口"""
        chain_server = getattr(self.driver, "_chained_proxy_server", None) if self.driver else None
        if chain_server is None:
            return
        try:
            chain_server.stop()
        except Exception as e:
            logger.debug(f"停止链式代理 server 失败: {e}")
        finally:
            try:
                # 防止重复 stop
                setattr(self.driver, "_chained_proxy_server", None)
            except Exception:
                pass


class AugmentTab(QWidget):
    """Augment注册管理Tab"""

    def __init__(self):
        super().__init__()
        self.augment_db = AugmentDBManager()
        self.data_db = DatabaseManager()
        self.worker: Optional[RegisterWorker] = None
        self.init_ui()
        self.load_accounts()
        self.update_proxy_status()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        splitter = QSplitter(Qt.Orientation.Vertical)

        # 上半部分
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        self.create_action_buttons(top_layout)
        self.create_log_console(top_layout)
        top_widget.setLayout(top_layout)
        splitter.addWidget(top_widget)

        # 下半部分
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()
        self.create_account_list(bottom_layout)
        bottom_widget.setLayout(bottom_layout)
        splitter.addWidget(bottom_widget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)
        self.setLayout(layout)

    def create_action_buttons(self, layout: QVBoxLayout):
        """创建操作按钮组"""
        group = QGroupBox("操作面板")
        grid = QGridLayout()

        self.register_btn = QPushButton("🚀 立即注册")
        self.register_btn.clicked.connect(self.start_register)
        grid.addWidget(self.register_btn, 0, 0)

        self.extract_btn = QPushButton("📥 提取账号信息")
        self.extract_btn.clicked.connect(self.extract_account_info)
        grid.addWidget(self.extract_btn, 0, 1)

        self.bind_card_btn = QPushButton("💳 绑定卡片")
        self.bind_card_btn.clicked.connect(self.bind_card)
        grid.addWidget(self.bind_card_btn, 0, 2)

        self.refresh_btn = QPushButton("🔄 刷新列表")
        self.refresh_btn.clicked.connect(self.load_accounts)
        grid.addWidget(self.refresh_btn, 1, 0)

        self.clear_logs_btn = QPushButton("🗑️ 清空日志")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        grid.addWidget(self.clear_logs_btn, 1, 1)

        self.stop_btn = QPushButton("⛔ 停止")
        self.stop_btn.clicked.connect(self.stop_register)
        self.stop_btn.setEnabled(False)
        grid.addWidget(self.stop_btn, 1, 2)

        self.proxy_config_btn = QPushButton("🌐 代理配置")
        self.proxy_config_btn.clicked.connect(self.open_proxy_config)
        grid.addWidget(self.proxy_config_btn, 2, 0)

        self.proxy_status_label = QLabel("代理: 未配置")
        grid.addWidget(self.proxy_status_label, 2, 1, 1, 2)

        group.setLayout(grid)
        layout.addWidget(group)

    def create_log_console(self, layout: QVBoxLayout):
        """创建日志控制台"""
        group = QGroupBox("日志控制台")
        console_layout = QVBoxLayout()

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(150)
        console_layout.addWidget(self.log_console)

        # 工具栏：复制全部日志（在控制台正下方靠右放）
        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        self.copy_logs_btn = QPushButton("📋 复制全部日志")
        self.copy_logs_btn.setToolTip("把日志面板里全部内容复制到剪贴板（Ctrl+C 也可复制选中内容）")
        self.copy_logs_btn.clicked.connect(self.copy_logs)
        toolbar.addWidget(self.copy_logs_btn)
        console_layout.addLayout(toolbar)

        group.setLayout(console_layout)
        layout.addWidget(group)

    def create_account_list(self, layout: QVBoxLayout):
        """创建账号列表"""
        group = QGroupBox("账号列表")
        list_layout = QVBoxLayout()

        stats_layout = QHBoxLayout()
        self.total_label = QLabel("总数: 0")
        self.registered_label = QLabel("已注册: 0")
        self.card_bound_label = QLabel("已绑卡: 0")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.registered_label)
        stats_layout.addWidget(self.card_bound_label)
        stats_layout.addStretch()
        list_layout.addLayout(stats_layout)

        self.account_table = QTableWidget()
        self.account_table.setColumnCount(8)
        self.account_table.setHorizontalHeaderLabels([
            "ID", "邮箱", "Tenant URL", "Credits", "Plan", "绑卡状态", "注册时间", "操作"
        ])
        self.account_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        list_layout.addWidget(self.account_table)

        group.setLayout(list_layout)
        layout.addWidget(group)

    def open_proxy_config(self):
        """打开代理配置对话框"""
        dialog = ProxyConfigDialog(self)
        if dialog.exec():
            self.update_proxy_status()

    def update_proxy_status(self):
        """更新代理状态显示"""
        proxy_manager = get_proxy_manager()
        count = proxy_manager.get_proxy_count()
        if count > 0:
            self.proxy_status_label.setText(f"代理: ✅ 已配置 ({count}个)")
            self.proxy_status_label.setStyleSheet("color: green;")
        else:
            self.proxy_status_label.setText("代理: ❌ 未配置")
            self.proxy_status_label.setStyleSheet("color: red;")

    def append_log(self, level: str, message: str):
        """添加日志"""
        self.log_console.append(f"[{level.upper()}] {message}")

    def clear_logs(self):
        """清空日志"""
        self.log_console.clear()

    def copy_logs(self):
        """把日志控制台里所有内容复制到系统剪贴板"""
        text = self.log_console.toPlainText()
        if not text:
            self.copy_logs_btn.setText("⚠️ 日志为空")
            QTimer.singleShot(1500, lambda: self.copy_logs_btn.setText("📋 复制全部日志"))
            return

        QApplication.clipboard().setText(text)

        # 短暂反馈：把按钮文字改成"已复制"，1.5 秒后恢复
        line_count = text.count("\n") + 1
        self.copy_logs_btn.setText(f"✅ 已复制 ({line_count} 行)")
        QTimer.singleShot(1500, lambda: self.copy_logs_btn.setText("📋 复制全部日志"))

    def start_register(self):
        """开始注册"""
        try:
            # 获取未使用的邮箱
            emails = self.data_db.get_all_emails(status='unused')
            if not emails:
                QMessageBox.warning(self, "警告", "没有可用的邮箱！")
                return

            email = emails[0].email

            # 禁用按钮
            self.register_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            # 创建工作线程
            self.worker = RegisterWorker(email, {})
            self.worker.progress.connect(self.append_log)
            self.worker.finished.connect(self.on_register_finished)
            self.worker.start()

            self.append_log("info", f"🚀 开始注册: {email}")

        except Exception as e:
            logger.error(f"启动注册失败: {e}")
            QMessageBox.critical(self, "错误", f"启动注册失败: {e}")

    def stop_register(self):
        """停止注册"""
        if self.worker and self.worker.isRunning():
            self.append_log("info", "⛔ 正在停止注册...")
            self.worker.stop()
            self.worker.wait()
            self.register_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def on_register_finished(self, success: bool, message: str):
        """注册完成回调"""
        self.register_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if success:
            self.append_log("info", f"✅ {message}")
            self.load_accounts()
        else:
            self.append_log("error", f"❌ {message}")

    def extract_account_info(self):
        """提取账号信息"""
        QMessageBox.information(self, "提示", "提取功能开发中...")

    def bind_card(self):
        """绑定卡片"""
        QMessageBox.information(self, "提示", "绑卡功能开发中...")

    def load_accounts(self):
        """加载账号列表"""
        try:
            accounts = self.augment_db.get_all_accounts()
            total = len(accounts)
            registered = len([a for a in accounts if a.status == 'registered'])
            card_bound = len([a for a in accounts if a.card_bound == 1])

            self.total_label.setText(f"总数: {total}")
            self.registered_label.setText(f"已注册: {registered}")
            self.card_bound_label.setText(f"已绑卡: {card_bound}")

            self.account_table.setRowCount(len(accounts))

            for row, account in enumerate(accounts):
                self.account_table.setItem(row, 0, QTableWidgetItem(str(account.id)))
                self.account_table.setItem(row, 1, QTableWidgetItem(account.email))
                self.account_table.setItem(row, 2, QTableWidgetItem(account.tenant_url or 'N/A'))
                self.account_table.setItem(row, 3, QTableWidgetItem(f"{account.credits}/{account.total_credits}"))
                self.account_table.setItem(row, 4, QTableWidgetItem(account.plan_name))

                card_status = "✅ 已绑卡" if account.card_bound == 1 else "❌ 未绑卡"
                card_item = QTableWidgetItem(card_status)
                if account.card_bound == 1:
                    card_item.setForeground(QColor('green'))
                self.account_table.setItem(row, 5, card_item)

                self.account_table.setItem(row, 6, QTableWidgetItem(account.registered_at or 'N/A'))

                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda aid=account.id: self.delete_account(aid))
                self.account_table.setCellWidget(row, 7, delete_btn)
        except Exception as e:
            logger.error(f"加载账号列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载账号列表失败: {e}")

    def delete_account(self, account_id: int):
        """删除账号"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个账号吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.augment_db.delete_account(account_id)
                self.load_accounts()
                QMessageBox.information(self, "成功", "账号已删除")
            except Exception as e:
                logger.error(f"删除账号失败: {e}")
                QMessageBox.critical(self, "错误", f"删除账号失败: {e}")


class ProxyConfigDialog(QDialog):
    """代理配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proxy_manager = get_proxy_manager()
        self.db_manager = AugmentDBManager()
        self.proxy_data = {}  # 存储代理数据的字典，key是行号
        self.init_ui()
        self.load_proxies()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("代理配置")
        self.setGeometry(100, 100, 900, 680)

        layout = QVBoxLayout()

        # ==================== 最上面：上游（系统）代理配置 ====================
        chain_group = QGroupBox("🔗 上游代理（系统代理 / 链式代理）")
        chain_layout = QVBoxLayout()

        chain_info = QLabel(
            "启用后，所有住宅代理会先经过这里设置的上游代理（例如本地 Clash）出墙，再连接住宅代理。\n"
            "适用场景：本机无法直连海外住宅代理（被墙拦截 / 住宅服务商拒绝国内 IP）。"
        )
        chain_info.setStyleSheet("font-size: 10px; color: #666;")
        chain_info.setWordWrap(True)
        chain_layout.addWidget(chain_info)

        chain_row = QHBoxLayout()

        self.chain_enabled_cb = QCheckBox("启用链式代理")
        chain_row.addWidget(self.chain_enabled_cb)

        chain_url_label = QLabel("上游代理:")
        chain_row.addWidget(chain_url_label)

        self.chain_url_edit = QLineEdit()
        self.chain_url_edit.setPlaceholderText(f"例如 {DEFAULT_UPSTREAM_URL}")
        chain_row.addWidget(self.chain_url_edit, stretch=1)

        save_chain_btn = QPushButton("💾 保存上游设置")
        save_chain_btn.clicked.connect(self.save_chain_only)
        chain_row.addWidget(save_chain_btn)

        chain_layout.addLayout(chain_row)
        chain_group.setLayout(chain_layout)
        layout.addWidget(chain_group)

        # 从配置文件加载初始值
        self._load_chain_settings_to_ui()

        # ==================== 上半部分：已保存的代理列表 ====================
        saved_label = QLabel("📋 已保存的代理列表")
        saved_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(saved_label)

        # 代理列表表格
        self.proxy_table = QTableWidget()
        self.proxy_table.setColumnCount(6)
        self.proxy_table.setHorizontalHeaderLabels(["选择", "代理地址", "IP", "位置", "商家", "操作"])
        self.proxy_table.setColumnWidth(0, 50)
        self.proxy_table.setColumnWidth(1, 180)
        self.proxy_table.setColumnWidth(2, 120)
        self.proxy_table.setColumnWidth(3, 140)
        self.proxy_table.setColumnWidth(4, 180)
        self.proxy_table.setColumnWidth(5, 100)
        self.proxy_table.setMaximumHeight(250)
        layout.addWidget(self.proxy_table)

        # ==================== 中间部分：添加新代理 ====================
        add_label = QLabel("➕ 添加新代理")
        add_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(add_label)

        # 说明文本
        info_label = QLabel(
            "每行一个代理，支持格式：\n"
            "• http://host:port  • http://user:pass@host:port  • socks5://host:port"
        )
        info_label.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(info_label)

        # 代理列表编辑框
        self.proxy_text = QPlainTextEdit()
        self.proxy_text.setPlaceholderText("输入新代理列表...")
        self.proxy_text.setMaximumHeight(150)
        layout.addWidget(self.proxy_text)

        # ==================== 下半部分：按钮 ====================
        button_layout = QHBoxLayout()

        save_btn = QPushButton("💾 保存并检测")
        save_btn.clicked.connect(self.save_proxies)
        button_layout.addWidget(save_btn)

        use_btn = QPushButton("✅ 使用选中的代理")
        use_btn.clicked.connect(self.use_selected_proxy)
        button_layout.addWidget(use_btn)

        rotate_btn = QPushButton("🔄 全部加入池（轮换模式）")
        rotate_btn.setToolTip(
            "把列表里所有代理一次性加到运行时池\n"
            "每次「立即注册」会自动按顺序轮换下一个 IP\n"
            "适合批量注册"
        )
        rotate_btn.clicked.connect(self.use_all_proxies_for_rotation)
        button_layout.addWidget(rotate_btn)

        clear_btn = QPushButton("🗑️ 清空所有")
        clear_btn.clicked.connect(self.clear_all_proxies)
        button_layout.addWidget(clear_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_proxies(self):
        """从数据库加载已保存的代理到表格"""
        try:
            # 从数据库获取所有代理
            proxies = self.db_manager.get_all_proxies()

            # 清空表格和数据字典
            self.proxy_table.setRowCount(0)
            self.proxy_data.clear()

            # 添加代理到表格
            for proxy in proxies:
                row = self.proxy_table.rowCount()
                self.proxy_table.insertRow(row)

                # 第0列：单选按钮
                radio_btn = QRadioButton()
                radio_btn.setStyleSheet("margin-left: 15px;")
                radio_btn.toggled.connect(lambda checked, r=row: self._on_proxy_selected(r, checked))
                self.proxy_table.setCellWidget(row, 0, radio_btn)

                # 存储代理数据到字典中
                self.proxy_data[row] = proxy

                # 第1列：代理地址
                proxy_url = proxy.get('proxy_url', '')
                self.proxy_table.setItem(row, 1, QTableWidgetItem(proxy_url))

                # 第2列：IP
                ip = proxy.get('ip_address', '-')
                self.proxy_table.setItem(row, 2, QTableWidgetItem(ip))

                # 第3列：位置
                location = proxy.get('location', '-')
                self.proxy_table.setItem(row, 3, QTableWidgetItem(location))

                # 第4列：商家
                provider = proxy.get('provider', '-')
                self.proxy_table.setItem(row, 4, QTableWidgetItem(provider))

                # 第5列：操作按钮（水平布局，图标按钮）
                op_layout = QHBoxLayout()
                op_layout.setContentsMargins(2, 2, 2, 2)
                op_layout.setSpacing(3)

                redetect_btn = QPushButton("🔄")
                redetect_btn.setMaximumWidth(35)
                redetect_btn.setMaximumHeight(30)
                redetect_btn.setToolTip("重新检测")
                # 使用 row 而不是 proxy，避免 clicked 信号传递的 bool 参数覆盖
                redetect_btn.clicked.connect(lambda r=row: self.redetect_proxy(r))

                delete_btn = QPushButton("🗑️")
                delete_btn.setMaximumWidth(35)
                delete_btn.setMaximumHeight(30)
                delete_btn.setToolTip("删除")
                # 使用 row 而不是 proxy，避免 clicked 信号传递的 bool 参数覆盖
                delete_btn.clicked.connect(lambda r=row: self.delete_proxy(r))

                op_layout.addWidget(redetect_btn)
                op_layout.addWidget(delete_btn)
                op_layout.addStretch()
                op_widget = QWidget()
                op_widget.setLayout(op_layout)
                self.proxy_table.setCellWidget(row, 5, op_widget)

            logger.info(f"✅ 从数据库加载了 {len(proxies)} 个代理")
        except Exception as e:
            logger.error(f"❌ 加载代理失败: {e}")
            QMessageBox.warning(self, "错误", f"加载代理失败: {e}")

    def save_proxies(self):
        """保存新代理到数据库并检测IP"""
        proxy_list = self.proxy_text.toPlainText().strip().split("\n")
        proxy_list = [p.strip() for p in proxy_list if p.strip()]

        if not proxy_list:
            QMessageBox.warning(self, "警告", "请输入至少一个代理！")
            return

        try:
            success_count = 0
            fail_count = 0

            # 添加代理到内存和数据库
            for proxy_str in proxy_list:
                try:
                    # 添加到内存
                    self.proxy_manager.add_proxies_from_list([proxy_str])

                    # 解析代理信息
                    proxy_config = self.proxy_manager._parse_proxy_string(proxy_str)

                    # 检测代理IP和地理位置
                    logger.info(f"🔍 正在检测代理: {proxy_str[:50]}...")
                    result = ProxyDetector.detect_proxy_info(proxy_config.to_url())

                    if result and result.get('success'):
                        # 保存到数据库
                        self.db_manager.add_proxy(
                            protocol=proxy_config.protocol,
                            host=proxy_config.host,
                            port=proxy_config.port,
                            username=proxy_config.username,
                            password=proxy_config.password,
                            ip_address=result.get('ip'),
                            location=result.get('location'),
                            as_number=result.get('as_number'),
                            provider=result.get('provider')
                        )
                        success_count += 1
                        logger.info(f"✅ 代理检测成功: {proxy_str[:50]}")
                    else:
                        # 检测失败，但仍然保存代理
                        error_msg = result.get('error', '未知错误') if result else '检测失败'
                        self.db_manager.add_proxy(
                            protocol=proxy_config.protocol,
                            host=proxy_config.host,
                            port=proxy_config.port,
                            username=proxy_config.username,
                            password=proxy_config.password
                        )
                        fail_count += 1
                        logger.warning(f"⚠️ 代理检测失败: {proxy_str[:50]} - {error_msg}")

                except Exception as e:
                    logger.error(f"处理代理失败: {proxy_str} - {e}")
                    fail_count += 1

            # 显示结果
            msg = f"✅ 成功: {success_count} 个\n⚠️ 失败: {fail_count} 个"
            QMessageBox.information(self, "保存完成", msg)

            # 清空输入框并重新加载表格
            self.proxy_text.clear()
            self.load_proxies()
            logger.info(f"✅ 代理配置完成，成功: {success_count}, 失败: {fail_count}")

        except Exception as e:
            logger.error(f"保存代理失败: {e}")
            QMessageBox.critical(self, "错误", f"保存代理失败: {e}")

    def clear_all_proxies(self):
        """清空所有代理"""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有代理吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.proxy_manager.clear_proxies()
            self.db_manager.clear_proxies()
            self.proxy_text.clear()
            self.load_proxies()
            QMessageBox.information(self, "成功", "已清空所有代理！")
            logger.info("✅ 代理已清空")

    def redetect_proxy(self, row: int):
        """重新检测代理信息"""
        try:
            # 从字典中获取代理数据
            proxy = self.proxy_data.get(row)

            if not proxy or not isinstance(proxy, dict):
                logger.error(f"❌ 无法获取代理数据: row={row}, proxy={proxy}")
                QMessageBox.critical(self, "错误", "无法获取代理数据")
                return

            proxy_url = proxy.get('proxy_url', '')
            proxy_id = proxy.get('id')

            if not proxy_url or not proxy_id:
                logger.error(f"❌ 代理信息不完整: url={proxy_url}, id={proxy_id}")
                QMessageBox.critical(self, "错误", "代理信息不完整")
                return

            logger.info(f"🔍 重新检测代理: {proxy_url[:50]}...")
            result = ProxyDetector.detect_proxy_info(proxy_url)

            # 检查检测结果是否成功
            if isinstance(result, dict) and result.get('success'):
                # 更新数据库
                update_result = self.db_manager.update_proxy_info(
                    proxy_id,
                    ip_address=result.get('ip'),
                    location=result.get('location'),
                    as_number=result.get('as_number'),
                    provider=result.get('provider')
                )

                if update_result:
                    msg = (
                        f"✅ 重新检测成功\n\n"
                        f"位置: {result.get('location')}\n"
                        f"IP: {result.get('ip')}\n"
                        f"AS号码: {result.get('as_number')}\n"
                        f"商家: {result.get('provider')}"
                    )
                    QMessageBox.information(self, "检测成功", msg)
                    logger.info(f"✅ 代理重新检测成功: {proxy_url[:50]}")

                    # 重新加载表格
                    self.load_proxies()
                else:
                    QMessageBox.warning(self, "更新失败", "检测成功但数据库更新失败")
                    logger.warning(f"⚠️ 数据库更新失败: {proxy_url[:50]}")
            else:
                error_msg = result.get('error', '未知错误') if isinstance(result, dict) else '检测失败'
                QMessageBox.warning(self, "检测失败", f"⚠️ 检测失败:\n{error_msg}")
                logger.warning(f"⚠️ 代理检测失败: {proxy_url[:50]} - {error_msg}")

        except Exception as e:
            logger.error(f"重新检测代理失败: {e}")
            QMessageBox.critical(self, "错误", f"重新检测失败: {e}")

    def delete_proxy(self, row: int):
        """删除代理"""
        try:
            # 从字典中获取代理数据
            proxy = self.proxy_data.get(row)

            if not proxy or not isinstance(proxy, dict):
                logger.error(f"❌ 无法获取代理数据: row={row}, proxy={proxy}")
                QMessageBox.critical(self, "错误", "无法获取代理数据")
                return

            proxy_url = proxy.get('proxy_url', '')
            proxy_id = proxy.get('id')

            if not proxy_url or not proxy_id:
                logger.error(f"❌ 代理信息不完整: url={proxy_url}, id={proxy_id}")
                QMessageBox.critical(self, "错误", "代理信息不完整")
                return

            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除代理 {proxy_url} 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.db_manager.delete_proxy(proxy_id)
                self.proxy_manager.remove_proxy(proxy_url)
                QMessageBox.information(self, "成功", "代理已删除！")
                logger.info(f"✅ 代理已删除: {proxy_url}")

                # 重新加载表格
                self.load_proxies()

        except Exception as e:
            logger.error(f"删除代理失败: {e}")
            QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def _on_proxy_selected(self, row: int, checked: bool):
        """当单选按钮被选中时调用"""
        try:
            # 只在选中时处理
            if not checked:
                return

            # 取消其他行的单选按钮
            for r in range(self.proxy_table.rowCount()):
                if r != row:
                    radio_btn = self.proxy_table.cellWidget(r, 0)
                    if radio_btn and isinstance(radio_btn, QRadioButton):
                        radio_btn.blockSignals(True)
                        radio_btn.setChecked(False)
                        radio_btn.blockSignals(False)

            # 获取选中的代理
            proxy = self.proxy_data.get(row)
            if proxy:
                proxy_url = proxy.get('proxy_url', '')
                logger.info(f"✅ 已选择代理: {proxy_url}")
        except Exception as e:
            logger.error(f"选择代理失败: {e}")

    def use_selected_proxy(self):
        """使用选中的代理"""
        try:
            # 查找被选中的单选按钮
            selected_row = -1
            for row in range(self.proxy_table.rowCount()):
                radio_btn = self.proxy_table.cellWidget(row, 0)
                if radio_btn and radio_btn.isChecked():
                    selected_row = row
                    break

            if selected_row < 0:
                QMessageBox.warning(self, "警告", "请先选择一个代理！")
                return

            # 从字典中获取代理数据
            proxy = self.proxy_data.get(selected_row)

            if not proxy:
                QMessageBox.warning(self, "错误", "无法获取代理信息！")
                return

            proxy_url = proxy.get('proxy_url', '')

            # 清空代理管理器中的所有代理
            self.proxy_manager.clear_proxies()

            # 添加选中的代理到代理管理器
            self.proxy_manager.add_proxies_from_list([proxy_url])

            msg = f"✅ 已加载代理:\n{proxy_url}\n\nIP: {proxy.get('ip_address', '-')}\n位置: {proxy.get('location', '-')}"
            QMessageBox.information(self, "成功", msg)
            logger.info(f"✅ 已加载代理: {proxy_url}")

            # 关闭对话框
            self.accept()

        except Exception as e:
            logger.error(f"加载代理失败: {e}")
            QMessageBox.critical(self, "错误", f"加载代理失败: {e}")

    def use_all_proxies_for_rotation(self):
        """把数据库里所有代理一次性加到运行时池，启用轮换模式"""
        try:
            proxies = self.db_manager.get_all_proxies()
            if not proxies:
                QMessageBox.warning(self, "提示", "代理列表为空，请先添加代理！")
                return

            proxy_urls = [p.get('proxy_url', '') for p in proxies if p.get('proxy_url')]
            if not proxy_urls:
                QMessageBox.warning(self, "错误", "数据库里没有有效的代理 URL")
                return

            # 先清空运行时池，再批量加入；ProxyManager.add_proxies_from_list 内部
            # 解析失败的会 logger.warning 跳过，不影响整体加入
            self.proxy_manager.clear_proxies()
            self.proxy_manager.add_proxies_from_list(proxy_urls)
            actual = self.proxy_manager.get_proxy_count()

            if actual == 0:
                QMessageBox.critical(
                    self, "错误",
                    "所有代理都解析失败，未加入任何条目。请检查代理格式。",
                )
                return

            skipped = len(proxy_urls) - actual
            extra = f"\n（{skipped} 个解析失败已跳过）" if skipped else ""
            msg = (
                f"✅ 已把 {actual} 个代理加入运行时池\n\n"
                f"每次「立即注册」会按顺序轮换下一个 IP\n"
                f"适合批量注册场景{extra}"
            )
            QMessageBox.information(self, "轮换模式已启用", msg)
            logger.info(f"✅ 已批量加入 {actual} 个代理到运行时池（轮换模式）")

            # 关闭对话框
            self.accept()

        except Exception as e:
            logger.error(f"批量加入代理失败: {e}")
            QMessageBox.critical(self, "错误", f"批量加入代理失败: {e}")

    # ==================== 上游（系统）代理 / 链式代理 ====================

    def _load_chain_settings_to_ui(self):
        """从配置文件读取链式代理设置并回填到 UI"""
        try:
            settings = load_chain_settings()
            self.chain_enabled_cb.setChecked(bool(settings.get("enabled", False)))
            self.chain_url_edit.setText(settings.get("upstream_url") or DEFAULT_UPSTREAM_URL)
        except Exception as e:
            logger.warning(f"⚠️ 加载链式代理配置失败: {e}")

    def _collect_chain_settings(self) -> tuple:
        """从 UI 读取链式代理设置，返回 (enabled, upstream_url)"""
        enabled = self.chain_enabled_cb.isChecked()
        url = self.chain_url_edit.text().strip() or DEFAULT_UPSTREAM_URL
        return enabled, url

    def save_chain_only(self):
        """仅保存上游代理设置（不影响代理列表）"""
        try:
            enabled, url = self._collect_chain_settings()

            # 启用时简单校验 URL
            if enabled:
                try:
                    self.proxy_manager._parse_proxy_string(url)
                except Exception as e:
                    QMessageBox.warning(self, "上游代理格式错误", f"无法解析: {url}\n\n{e}")
                    return

            save_chain_settings(enabled, url)
            state = "已启用" if enabled else "已关闭"
            QMessageBox.information(self, "保存成功", f"上游代理{state}\n地址: {url}")
        except Exception as e:
            logger.error(f"保存上游代理设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存上游代理设置失败: {e}")
