"""
标签分类栏组件
位于Tab页签下方，用于按标签筛选任务
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QFrame, QDialog, QCheckBox,
                             QGridLayout, QDialogButtonBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from managers.data_manager import DataManager, TaskType
import config.config as config


class TagFilterBar(QWidget):
    """标签分类栏组件 - 显示可点击的标签按钮进行筛选"""
    
    # 信号：当用户点击某个标签时发出
    tagClicked = pyqtSignal(str)  # 发出标签名，""表示全部
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_task_type = TaskType.DAILY
        self.active_tag = ""  # 当前激活的标签
        self.max_display = config.TAG_FILTER_MAX_DISPLAY  # 从配置读取显示上限
        self.tag_buttons = {}  # 标签按钮字典
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)
        
        # 创建标题和按钮区域（紧凑布局）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题标签
        self.title_label = QLabel("标签:")
        self.title_label.setStyleSheet("font-weight: bold; color: #666; font-size: 12px;")
        header_layout.addWidget(self.title_label)
        
        # 创建滚动区域容纳标签按钮
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setMaximumHeight(40)
        
        # 标签按钮容器
        self.tags_container = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.addStretch()
        
        self.scroll_area.setWidget(self.tags_container)
        header_layout.addWidget(self.scroll_area, stretch=1)
        
        # 编辑按钮
        self.edit_btn = QPushButton("···")
        self.edit_btn.setFixedSize(32, 26)
        self.edit_btn.setToolTip("编辑显示标签")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-weight: bold;
                color: #666;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.edit_btn.clicked.connect(self.show_tag_editor)
        header_layout.addWidget(self.edit_btn)
        
        main_layout.addLayout(header_layout)
        
        # 设置样式
        self.setStyleSheet("""
            TagFilterBar {
                background-color: transparent;
            }
        """)
        self.setMaximumHeight(45)
    
    def set_task_type(self, task_type: TaskType):
        """设置当前任务类型，刷新标签显示"""
        self.current_task_type = task_type
        self.active_tag = ""  # 切换类型时重置筛选
        self.refresh_tags()
    
    def refresh_tags(self):
        """刷新标签按钮显示"""
        # 清除现有按钮
        self.clear_tags()
        
        if not self.data_manager:
            return
        
        # 获取可见标签配置
        visible_tags = self.get_visible_tags()
        
        # 添加"全部"按钮
        self.add_tag_button("全部", is_all=True)
        
        # 添加标签按钮
        for tag in visible_tags[:self.max_display]:
            self.add_tag_button(tag)
        
        # 更新按钮状态
        self.update_button_states()
    
    def clear_tags(self):
        """清除所有标签按钮"""
        # 移除所有按钮
        for btn in self.tag_buttons.values():
            btn.setParent(None)
            btn.deleteLater()
        self.tag_buttons.clear()
        
        # 移除stretch
        while self.tags_layout.count() > 0:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
    
    def add_tag_button(self, tag: str, is_all: bool = False):
        """添加标签按钮"""
        btn = QPushButton(tag)
        btn.setCheckable(True)
        btn.setFixedHeight(26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 根据文本长度设置宽度（紧凑布局）
        text_width = len(tag) * 12 + 20
        btn.setFixedWidth(min(max(text_width, 50), 100))
        
        # 设置样式
        btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #999;
            }
            QPushButton:checked {
                background-color: #2196F3;
                border-color: #1976D2;
                color: white;
            }
        """)
        
        # 连接点击事件
        btn.clicked.connect(lambda checked, t=tag: self.on_tag_clicked(t))
        
        # 插入到stretch之前
        self.tags_layout.insertWidget(len(self.tag_buttons), btn)
        self.tag_buttons[tag] = btn
    
    def on_tag_clicked(self, tag: str):
        """标签按钮点击处理"""
        if tag == "全部":
            self.active_tag = ""
        elif self.active_tag == tag:
            # 再次点击取消筛选
            self.active_tag = ""
        else:
            self.active_tag = tag
        
        self.update_button_states()
        self.tagClicked.emit(self.active_tag)
    
    def update_button_states(self):
        """更新按钮选中状态"""
        for tag, btn in self.tag_buttons.items():
            if tag == "全部":
                btn.setChecked(self.active_tag == "")
            else:
                btn.setChecked(tag == self.active_tag)
    
    def get_visible_tags(self) -> list:
        """获取当前应显示的标签列表"""
        if not self.data_manager:
            return []
        
        # 从配置读取
        config_key = f"visible_tags_{self.current_task_type.value}"
        config_value = self.data_manager.get_config(config_key, "")
        
        if config_value:
            # 使用用户配置的标签
            tags = [t.strip() for t in config_value.split(",") if t.strip()]
            if tags:
                return tags
        
        # 无配置时，自动获取使用频率最高的标签
        return self.get_top_tags()
    
    def get_top_tags(self) -> list:
        """获取使用频率最高的标签"""
        if not self.data_manager:
            return []
        
        # 收集所有标签及其使用次数
        tag_count = {}
        
        if self.current_task_type == TaskType.DAILY:
            tasks = self.data_manager.get_daily_tasks()
        elif self.current_task_type == TaskType.TODO:
            tasks = self.data_manager.get_todo_tasks()
        else:
            tasks = self.data_manager.get_entertainment_tasks()
        
        for task in tasks:
            if task.tags:
                for tag in task.tags.split(","):
                    tag = tag.strip()
                    if tag:
                        tag_count[tag] = tag_count.get(tag, 0) + 1
        
        # 按使用次数排序，取前max_display个
        sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, count in sorted_tags[:self.max_display]]
    
    def get_all_tags(self) -> list:
        """获取该类型任务的所有标签"""
        if not self.data_manager:
            return []
        
        tags = set()
        
        if self.current_task_type == TaskType.DAILY:
            tasks = self.data_manager.get_daily_tasks()
        elif self.current_task_type == TaskType.TODO:
            tasks = self.data_manager.get_todo_tasks()
        else:
            tasks = self.data_manager.get_entertainment_tasks()
        
        for task in tasks:
            if task.tags:
                for tag in task.tags.split(","):
                    tag = tag.strip()
                    if tag:
                        tags.add(tag)
        
        return sorted(list(tags))
    
    def show_tag_editor(self):
        """显示标签编辑对话框"""
        dialog = TagEditorDialog(self, self.data_manager, self.current_task_type, self.max_display)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_tags = dialog.get_selected_tags()
            # 保存配置
            config_key = f"visible_tags_{self.current_task_type.value}"
            self.data_manager.set_config(config_key, ",".join(selected_tags))
            # 刷新显示
            self.refresh_tags()


class TagEditorDialog(QDialog):
    """标签编辑对话框 - 让用户选择要显示的标签"""
    
    def __init__(self, parent=None, data_manager=None, task_type=None, max_display=10):
        super().__init__(parent)
        self.data_manager = data_manager
        self.task_type = task_type
        self.max_display = max_display
        self.checkboxes = {}
        self.init_ui()
    
    def init_ui(self):
        """初始化对话框界面"""
        self.setWindowTitle("编辑显示标签")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        
        # 说明文字
        info_label = QLabel(f"选择要显示在标签栏的标签（最多 {self.max_display} 个）：")
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # 标签选择区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(10)
        
        # 获取所有标签和当前配置
        all_tags = self.get_all_tags()
        config_key = f"visible_tags_{self.task_type.value}"
        current_config = self.data_manager.get_config(config_key, "")
        current_tags = set(t.strip() for t in current_config.split(",") if t.strip())
        
        # 创建复选框
        row, col = 0, 0
        for tag in all_tags:
            checkbox = QCheckBox(tag)
            checkbox.setChecked(tag in current_tags)
            checkbox.stateChanged.connect(self.on_checkbox_changed)
            self.checkboxes[tag] = checkbox
            grid.addWidget(checkbox, row, col)
            
            col += 1
            if col >= 3:  # 每行3个
                col = 0
                row += 1
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # 提示标签
        self.hint_label = QLabel(f"已选择: {len(current_tags)} / {self.max_display}")
        self.hint_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        layout.addWidget(self.hint_label)
        
        # 按钮区域
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
    
    def get_all_tags(self) -> list:
        """获取所有可用标签"""
        if not self.data_manager:
            return []
        
        tags = set()
        
        if self.task_type == TaskType.DAILY:
            tasks = self.data_manager.get_daily_tasks()
        elif self.task_type == TaskType.TODO:
            tasks = self.data_manager.get_todo_tasks()
        else:
            tasks = self.data_manager.get_entertainment_tasks()
        
        for task in tasks:
            if task.tags:
                for tag in task.tags.split(","):
                    tag = tag.strip()
                    if tag:
                        tags.add(tag)
        
        return sorted(list(tags))
    
    def on_checkbox_changed(self):
        """复选框状态变化处理"""
        selected_count = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        self.hint_label.setText(f"已选择: {selected_count} / {self.max_display}")
        
        # 超过限制时提示
        if selected_count > self.max_display:
            self.hint_label.setStyleSheet("color: #F44336; font-weight: bold;")
            self.hint_label.setText(f"已选择: {selected_count} / {self.max_display} （超出限制！）")
        else:
            self.hint_label.setStyleSheet("color: #2196F3; font-weight: bold;")
    
    def on_ok(self):
        """确定按钮处理"""
        selected_count = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        
        if selected_count > self.max_display:
            QMessageBox.warning(self, "警告", f"最多只能选择 {self.max_display} 个标签！")
            return
        
        self.accept()
    
    def get_selected_tags(self) -> list:
        """获取选中的标签列表"""
        return [tag for tag, cb in self.checkboxes.items() if cb.isChecked()]