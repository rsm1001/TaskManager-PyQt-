"""
标签选择组件 - 可重用的标签选择控件
支持各类别独立标签库
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QScrollArea, QCheckBox, QPushButton, QInputDialog, 
                            QMessageBox, QLineEdit, QLabel, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from managers.data_manager import TaskType


class TagSelectorWidget(QWidget):
    """可重用的标签选择组件"""
    tagsChanged = pyqtSignal(str)  # 发出标签变化信号（逗号分隔的字符串）

    def __init__(self, parent=None, data_manager=None, initial_tags="", task_type=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.task_type = task_type  # 任务类型，用于隔离标签库
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
        self.tags_inner_layout = QGridLayout()  # 改为网格布局，多列显示
        
        self.scroll_widget.setLayout(self.tags_inner_layout)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(150)  # 设置最大高度
        
        tags_layout.addWidget(self.scroll_area)
        
        # 标签按钮区域
        button_layout = QHBoxLayout()
        
        # 添加新标签按钮
        self.add_tag_btn = QPushButton("添加标签")
        self.add_tag_btn.clicked.connect(self.add_new_tag)
        button_layout.addWidget(self.add_tag_btn)
        
        # 删除选中标签按钮
        self.delete_tag_btn = QPushButton("删除标签")
        self.delete_tag_btn.clicked.connect(self.delete_selected_tag)
        button_layout.addWidget(self.delete_tag_btn)
        
        button_layout.addStretch()  # 弹性空间
        tags_layout.addLayout(button_layout)
        
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)
        self.setLayout(layout)

    def _get_category(self) -> str:
        """获取当前类别标识"""
        if self.task_type is None:
            return ''
        return self.task_type.value if hasattr(self.task_type, 'value') else str(self.task_type)

    def load_tags_from_category(self):
        """从类别独立标签库加载标签"""
        self.all_tags = set()
        category = self._get_category()
        
        if self.data_manager and category:
            category_tags = self.data_manager.get_all_tags(category)
            self.all_tags.update(category_tags)

    def refresh_tags(self):
        """刷新标签列表（从类别独立标签库加载）"""
        self.load_tags_from_category()
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
        
        # 从类别独立标签库加载所有可用标签
        self.load_tags_from_category()
        
        # 如果有初始标签，确保它们也在 all_tags 中
        if tags_str:
            self.all_tags.update(self.selected_tags)
        
        self._create_checkboxes()

    def _create_checkboxes(self):
        """创建标签复选框（多列网格布局）"""
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

        # 网格布局列数
        num_columns = 3
        
        # 创建标签复选框（按字母排序），按行优先填充网格
        row, col = 0, 0
        for tag in sorted(self.all_tags):
            checkbox = QCheckBox(tag)
            checkbox.setChecked(tag in self.selected_tags)
            checkbox.stateChanged.connect(self.on_tag_state_changed)
            self.tag_checkboxes[tag] = checkbox
            self.tags_inner_layout.addWidget(checkbox, row, col)
            
            col += 1
            if col >= num_columns:
                col = 0
                row += 1
        
        # 如果没有标签，显示提示
        if not self.all_tags:
            label = QLabel('暂无标签，点击"添加标签"创建')
            label.setStyleSheet("color: gray;")
            self.tags_inner_layout.addWidget(label, 0, 0, 1, num_columns)
        
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
                # 跨 3 列显示
                self.tags_inner_layout.addWidget(no_match_label, 0, 0, 1, 3)
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
        """添加新标签（保存到类别独立标签库）"""
        tag_name, ok = QInputDialog.getText(self, "添加新标签", "请输入标签名称:")
        if ok and tag_name.strip():
            tag = tag_name.strip()
            category = self._get_category()
            
            # 保存到类别独立标签库
            if self.data_manager and category:
                self.data_manager.add_tag(tag, category)
            
            # 更新本地标签集
            if tag not in self.all_tags:
                self.all_tags.add(tag)
            
            # 选中新添加的标签
            self.selected_tags.add(tag)
            
            # 重新创建复选框
            self._create_checkboxes()
            
            # 清空搜索框以显示新标签
            if hasattr(self, 'search_edit'):
                self.search_edit.clear()
            
            self.tagsChanged.emit(self.get_selected_tags())

    def delete_selected_tag(self):
        """删除选中的标签（仅删除未使用的标签）"""
        if not self.selected_tags:
            QMessageBox.information(self, "提示", "请先选择一个标签进行删除")
            return
        
        # 获取选中的标签
        tags_to_delete = sorted(self.selected_tags)
        if len(tags_to_delete) == 1:
            tag = tags_to_delete[0]
            confirm_msg = f"确定要删除标签 '{tag}' 吗？"
        else:
            tag = tags_to_delete[0]
            confirm_msg = f"确定要删除选中的 {len(tags_to_delete)} 个标签吗？"
        
        reply = QMessageBox.question(self, "确认删除", confirm_msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 尝试删除每个选中的标签
        deleted_tags = []
        failed_tags = []
        
        for tag in tags_to_delete:
            if self.data_manager:
                category = self._get_category()
                # 检查标签是否被使用，如果未被使用则删除（类别独立）
                if self.data_manager.delete_tag(tag, category):
                    deleted_tags.append(tag)
                    # 从本地标签集中移除
                    self.all_tags.discard(tag)
                    self.selected_tags.discard(tag)
                else:
                    failed_tags.append(tag)
            else:
                # 没有 data_manager，只从本地移除
                self.all_tags.discard(tag)
                self.selected_tags.discard(tag)
                deleted_tags.append(tag)
        
        # 显示结果
        if failed_tags:
            QMessageBox.warning(self, "部分删除失败", 
                              f"以下标签正在被任务使用，无法删除：\n{', '.join(failed_tags)}")
        
        if deleted_tags:
            # 重新创建复选框
            self._create_checkboxes()
            
            # 清空搜索框
            if hasattr(self, 'search_edit'):
                self.search_edit.clear()
            
            self.tagsChanged.emit(self.get_selected_tags())
