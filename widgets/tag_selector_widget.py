"""
标签选择组件 - 可重用的标签选择控件
简化版：使用逗号分隔字符串存储标签
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QScrollArea, QCheckBox, QPushButton, QInputDialog, 
                            QMessageBox, QLineEdit, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal


class TagSelectorWidget(QWidget):
    """可重用的标签选择组件"""
    tagsChanged = pyqtSignal(str)  # 发出标签变化信号（逗号分隔的字符串）

    def __init__(self, parent=None, data_manager=None, initial_tags=""):
        super().__init__(parent)
        self.data_manager = data_manager
        self.all_tags = set()  # 存储所有可用标签
        self.selected_tags = set()  # 存储当前选中的标签
        self.tag_checkboxes = {}  # 存储标签复选框映射
        self.init_ui()
        self.load_tags(initial_tags)

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 标签选择区域
        tags_group = QGroupBox("标签选择")
        tags_layout = QVBoxLayout()
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('搜索:'))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('输入标签名称进行筛选...')
        self.search_edit.textChanged.connect(self.filter_tags)
        search_layout.addWidget(self.search_edit)
        tags_layout.addLayout(search_layout)
        
        # 创建滚动区域以容纳可能很多的标签
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.tags_inner_layout = QVBoxLayout()
        
        self.scroll_widget.setLayout(self.tags_inner_layout)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(150)  # 设置最大高度
        
        tags_layout.addWidget(self.scroll_area)
        
        # 标签按钮区域
        button_layout = QHBoxLayout()
        
        # 刷新标签按钮
        self.refresh_tags_btn = QPushButton("刷新标签")
        self.refresh_tags_btn.clicked.connect(self.refresh_tags)
        button_layout.addWidget(self.refresh_tags_btn)
        
        # 添加新标签按钮
        self.add_tag_btn = QPushButton("添加标签")
        self.add_tag_btn.clicked.connect(self.add_new_tag)
        button_layout.addWidget(self.add_tag_btn)
        
        button_layout.addStretch()  # 弹性空间
        tags_layout.addLayout(button_layout)
        
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)
        self.setLayout(layout)

    def refresh_tags(self):
        """刷新标签列表（从所有任务中收集）"""
        if not self.data_manager:
            return
        
        # 从所有任务中收集标签
        self.all_tags = set()
        
        # 收集每日任务的标签
        for task in self.data_manager.get_daily_tasks():
            if task.tags:
                self.all_tags.update(tag.strip() for tag in task.tags.split(',') if tag.strip())
        
        # 收集待办事项的标签
        for task in self.data_manager.get_todo_tasks():
            if task.tags:
                self.all_tags.update(tag.strip() for tag in task.tags.split(',') if tag.strip())
        
        # 收集娱乐任务的标签
        for task in self.data_manager.get_entertainment_tasks():
            if task.tags:
                self.all_tags.update(tag.strip() for tag in task.tags.split(',') if tag.strip())
        
        # 重新创建复选框
        self._create_checkboxes()

    def load_tags(self, tags_str=""):
        """加载标签
        
        Args:
            tags_str: 逗号分隔的标签字符串
        """
        # 解析当前选中的标签
        self.selected_tags = set()
        if tags_str:
            self.selected_tags = set(tag.strip() for tag in tags_str.split(',') if tag.strip())
            self.all_tags.update(self.selected_tags)
        
        # 如果有数据管理器，从所有任务中收集标签
        if self.data_manager:
            self.refresh_tags()
        else:
            self._create_checkboxes()

    def _create_checkboxes(self):
        """创建标签复选框"""
        # 清除现有的复选框
        for checkbox in self.tag_checkboxes.values():
            checkbox.setParent(None)
            checkbox.deleteLater()
        self.tag_checkboxes.clear()
        
        # 清空内部布局
        while self.tags_inner_layout.count():
            item = self.tags_inner_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # 创建标签复选框（按字母排序）
        for tag in sorted(self.all_tags):
            checkbox = QCheckBox(tag)
            checkbox.setChecked(tag in self.selected_tags)
            checkbox.stateChanged.connect(self.on_tag_state_changed)
            self.tag_checkboxes[tag] = checkbox
            self.tags_inner_layout.addWidget(checkbox)
        
        # 如果没有标签，显示提示
        if not self.all_tags:
            label = QLabel('暂无标签，点击"添加标签"创建')
            label.setStyleSheet("color: gray;")
            self.tags_inner_layout.addWidget(label)
        
        # 应用当前的搜索过滤
        self.filter_tags(self.search_edit.text() if hasattr(self, 'search_edit') else '')

    def get_selected_tags(self):
        """获取选中的标签（逗号分隔的字符串）"""
        return ','.join(sorted(self.selected_tags))

    def set_selected_tags(self, tags_str):
        """设置选中的标签
        
        Args:
            tags_str: 逗号分隔的标签字符串
        """
        self.selected_tags = set()
        if tags_str:
            self.selected_tags = set(tag.strip() for tag in tags_str.split(',') if tag.strip())
        self._update_checkbox_states()
        self.tagsChanged.emit(self.get_selected_tags())

    def _update_checkbox_states(self):
        """更新复选框状态"""
        for tag, checkbox in self.tag_checkboxes.items():
            checkbox.setChecked(tag in self.selected_tags)

    def on_tag_state_changed(self, state):
        """处理标签选择状态变化"""
        sender = self.sender()
        if not sender:
            return
        
        tag = sender.text()
        if state == Qt.CheckState.Checked.value:
            self.selected_tags.add(tag)
        else:
            self.selected_tags.discard(tag)
        
        # 发出信号通知标签已更改
        self.tagsChanged.emit(self.get_selected_tags())

    def filter_tags(self, search_text):
        """根据搜索文本过滤标签显示
        
        Args:
            search_text: 搜索关键词
        """
        search_text = search_text.lower().strip()
        has_visible = False
        
        for tag, checkbox in self.tag_checkboxes.items():
            if search_text in tag.lower():
                checkbox.setVisible(True)
                has_visible = True
            else:
                checkbox.setVisible(False)
        
        # 显示或隐藏"无匹配"提示
        if not has_visible and self.all_tags:
            # 检查是否已存在无匹配提示
            found = False
            for i in range(self.tags_inner_layout.count()):
                item = self.tags_inner_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, QLabel) and widget.objectName() == 'no_match_label':
                        widget.setVisible(True)
                        found = True
                        break
            if not found:
                no_match_label = QLabel('无匹配标签')
                no_match_label.setObjectName('no_match_label')
                no_match_label.setStyleSheet("color: gray;")
                self.tags_inner_layout.addWidget(no_match_label)
        else:
            # 隐藏无匹配提示
            for i in range(self.tags_inner_layout.count()):
                item = self.tags_inner_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, QLabel) and widget.objectName() == 'no_match_label':
                        widget.setVisible(False)
                        break

    def add_new_tag(self):
        """添加新标签"""
        tag_name, ok = QInputDialog.getText(self, "添加新标签", "请输入标签名称:")
        if ok and tag_name.strip():
            tag = tag_name.strip()
            if tag not in self.all_tags:
                self.all_tags.add(tag)
                self.selected_tags.add(tag)
                self._create_checkboxes()
                # 清空搜索框以显示新标签
                self.search_edit.clear()
                self.tagsChanged.emit(self.get_selected_tags())
            else:
                # 标签已存在，直接选中
                self.selected_tags.add(tag)
                self._update_checkbox_states()
                # 清空搜索框以确保用户能看到选中的标签
                self.search_edit.clear()
                self.tagsChanged.emit(self.get_selected_tags())
