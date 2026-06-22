"""
Task Manager - 任务编辑对话框模块
将原来的 TaskEditDialog 类从 main.py 中分离出来以实现解耦
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTextEdit,
                             QLabel, QComboBox, QCheckBox, QDateEdit, QPushButton, QGridLayout,
                             QGroupBox, QScrollArea, QWidget, QSpinBox)
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox
from managers.data_manager import TaskType
from managers.priority import PRIORITY_LABELS, LABEL_TO_KEY, DEFAULT_PRIORITY, get_priority_label
from widgets.tag_selector_widget import TagSelectorWidget
from config.config import ESTIMATED_DURATION_QUICK_OPTIONS
from datetime import timedelta
import datetime
import json
import uuid


class TaskEditDialog(QDialog):
    """任务编辑对话框"""

    def __init__(self, task_type: TaskType, parent=None, task=None, data_manager=None):
        super().__init__(parent)
        self.task_type = task_type
        self.task = task
        self.data_manager = data_manager
        self._subtasks = []  # 仅 TODO 类型使用：list of {id, title, completed}
        self.init_ui()
        if task:
            self.load_task_data()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"{'编辑' if self.task else '添加'}{self.get_task_type_name()}")
        self.setModal(True)
        self.resize(560, 620)

        layout = QVBoxLayout()

        # 标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel('标题:'))
        self.title_edit = QLineEdit()
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

        # 描述
        layout.addWidget(QLabel('描述:'))
        self.desc_edit = QTextEdit()
        layout.addWidget(self.desc_edit)

        # 标签选择组件
        self.tag_selector = TagSelectorWidget(
            parent=self,
            data_manager=self.data_manager,
            initial_tags=self.task.tags if self.task else "",
            task_type=self.task_type
        )
        layout.addWidget(self.tag_selector)

        # 任务特定字段
        if self.task_type == TaskType.DAILY:
            weekday_layout = QHBoxLayout()
            weekday_layout.addWidget(QLabel('星期:'))
            self.weekday_combo = QComboBox()
            self.weekday_combo.addItems(['每天', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'])
            weekday_layout.addWidget(self.weekday_combo)
            layout.addLayout(weekday_layout)

            # 分类选择
            category_layout = QHBoxLayout()
            category_layout.addWidget(QLabel('分类:'))
            self.folder_combo = QComboBox()
            self.folder_combo.setEditable(True)
            self.folder_combo.setMinimumWidth(150)
            self._load_categories('daily')
            category_layout.addWidget(self.folder_combo)

            new_cat_btn = QPushButton('新建')
            new_cat_btn.clicked.connect(lambda: self._create_new_category('daily'))
            category_layout.addWidget(new_cat_btn)
            layout.addLayout(category_layout)

            # 优先级选择
            priority_layout = QHBoxLayout()
            priority_layout.addWidget(QLabel('优先级:'))
            self.priority_combo = QComboBox()
            self.priority_combo.addItems(PRIORITY_LABELS)
            priority_layout.addWidget(self.priority_combo)
            priority_layout.addStretch()
            layout.addLayout(priority_layout)

            # 用时预估选择
            duration_layout = QHBoxLayout()
            duration_layout.addWidget(QLabel('用时预估:'))
            self.duration_spin = QSpinBox()
            self.duration_spin.setRange(0, 999)
            self.duration_spin.setSuffix(" 分钟")
            self.duration_spin.setValue(0)
            duration_layout.addWidget(self.duration_spin)

            # 快设置按钮
            for mins in ESTIMATED_DURATION_QUICK_OPTIONS:
                btn = QPushButton(f'{mins}分钟')
                btn.setMinimumWidth(60)
                btn.clicked.connect(lambda checked, m=mins: self.duration_spin.setValue(m))
                duration_layout.addWidget(btn)
            duration_layout.addStretch()
            layout.addLayout(duration_layout)
        elif self.task_type == TaskType.TODO:
            deadline_layout = QHBoxLayout()
            deadline_layout.addWidget(QLabel('截止日期:'))
            self.deadline_date = QDateEdit()
            self.deadline_date.setDisplayFormat('yyyy-MM-dd')
            self.deadline_date.setCalendarPopup(True)
            # 设置最小日期以避免2000年的默认值问题
            self.deadline_date.setMinimumDate(QDate.currentDate())
            self.deadline_date.setDate(QDate.currentDate())  # 设置为今天
            deadline_layout.addWidget(self.deadline_date)
            layout.addLayout(deadline_layout)

            # 添加快速设置截止日期按钮
            quick_set_layout = QHBoxLayout()
            quick_set_layout.addWidget(QLabel('快速设置:'))

            btn_3days = QPushButton('3天后')
            btn_3days.clicked.connect(lambda: self.set_deadline_days(3))
            quick_set_layout.addWidget(btn_3days)

            btn_7days = QPushButton('7天后')
            btn_7days.clicked.connect(lambda: self.set_deadline_days(7))
            quick_set_layout.addWidget(btn_7days)

            btn_14days = QPushButton('2周后')
            btn_14days.clicked.connect(lambda: self.set_deadline_days(14))
            quick_set_layout.addWidget(btn_14days)

            btn_30days = QPushButton('1个月后')
            btn_30days.clicked.connect(lambda: self.set_deadline_days(30))
            quick_set_layout.addWidget(btn_30days)

            btn_60days = QPushButton('2个月后')
            btn_60days.clicked.connect(lambda: self.set_deadline_days(60))
            quick_set_layout.addWidget(btn_60days)

            quick_set_layout.addStretch()  # 添加弹性空间，使按钮靠左对齐
            layout.addLayout(quick_set_layout)

            # 分类选择
            category_layout = QHBoxLayout()
            category_layout.addWidget(QLabel('分类:'))
            self.folder_combo = QComboBox()
            self.folder_combo.setEditable(True)
            self.folder_combo.setMinimumWidth(150)
            self._load_categories('todo')
            category_layout.addWidget(self.folder_combo)

            new_cat_btn = QPushButton('新建')
            new_cat_btn.clicked.connect(lambda: self._create_new_category('todo'))
            category_layout.addWidget(new_cat_btn)
            layout.addLayout(category_layout)

            # 优先级选择
            priority_layout = QHBoxLayout()
            priority_layout.addWidget(QLabel('优先级:'))
            self.priority_combo = QComboBox()
            self.priority_combo.addItems(PRIORITY_LABELS)
            priority_layout.addWidget(self.priority_combo)
            priority_layout.addStretch()
            layout.addLayout(priority_layout)

            # 用时预估选择
            duration_layout = QHBoxLayout()
            duration_layout.addWidget(QLabel('用时预估:'))
            self.duration_spin = QSpinBox()
            self.duration_spin.setRange(0, 999)
            self.duration_spin.setSuffix(" 分钟")
            self.duration_spin.setValue(0)
            duration_layout.addWidget(self.duration_spin)

            # 快设置按钮
            for mins in ESTIMATED_DURATION_QUICK_OPTIONS:
                btn = QPushButton(f'{mins}分钟')
                btn.setMinimumWidth(60)
                btn.clicked.connect(lambda checked, m=mins: self.duration_spin.setValue(m))
                duration_layout.addWidget(btn)
            duration_layout.addStretch()
            layout.addLayout(duration_layout)
        elif self.task_type == TaskType.ENTERTAINMENT:
            category_layout = QHBoxLayout()
            category_layout.addWidget(QLabel('类别:'))
            self.category_combo = QComboBox()
            self.category_combo.addItems(['general', 'games', 'movies', 'sports', 'reading', 'music', 'other'])
            category_layout.addWidget(self.category_combo)
            layout.addLayout(category_layout)

            # 分类选择（复用 fun_category 字段）
            folder_layout = QHBoxLayout()
            folder_layout.addWidget(QLabel('分类:'))
            self.folder_combo = QComboBox()
            self.folder_combo.setEditable(True)
            self.folder_combo.setMinimumWidth(150)
            self._load_categories('entertainment')
            folder_layout.addWidget(self.folder_combo)

            new_cat_btn = QPushButton('新建')
            new_cat_btn.clicked.connect(lambda: self._create_new_category('entertainment'))
            folder_layout.addWidget(new_cat_btn)
            layout.addLayout(folder_layout)

            # 优先级选择
            priority_layout = QHBoxLayout()
            priority_layout.addWidget(QLabel('优先级:'))
            self.priority_combo = QComboBox()
            self.priority_combo.addItems(PRIORITY_LABELS)
            priority_layout.addWidget(self.priority_combo)
            priority_layout.addStretch()
            layout.addLayout(priority_layout)

            # 用时预估选择
            duration_layout = QHBoxLayout()
            duration_layout.addWidget(QLabel('用时预估:'))
            self.duration_spin = QSpinBox()
            self.duration_spin.setRange(0, 999)
            self.duration_spin.setSuffix(" 分钟")
            self.duration_spin.setValue(0)
            duration_layout.addWidget(self.duration_spin)

            # 快设置按钮
            for mins in ESTIMATED_DURATION_QUICK_OPTIONS:
                btn = QPushButton(f'{mins}分钟')
                btn.setMinimumWidth(60)
                btn.clicked.connect(lambda checked, m=mins: self.duration_spin.setValue(m))
                duration_layout.addWidget(btn)
            duration_layout.addStretch()
            layout.addLayout(duration_layout)

        # 子任务（检查项）区域——三类任务共用
        self._build_subtasks_section(layout)

        # 完成状态
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel('状态:'))
        self.status_combo = QComboBox()
        self.status_combo.addItems(['进行中', '已完成', '暂弃'])
        status_layout.addWidget(self.status_combo)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton('确定')
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _build_subtasks_section(self, parent_layout):
        """构建子任务（检查项）UI 区域。仅 TODO 类型使用。"""
        group = QGroupBox("子任务")
        v = QVBoxLayout()

        header = QHBoxLayout()
        header.addWidget(QLabel("检查项列表"))
        header.addStretch()
        self.subtask_progress_label = QLabel("已完成 0/0")
        header.addWidget(self.subtask_progress_label)
        v.addLayout(header)

        self.subtask_scroll = QScrollArea()
        self.subtask_scroll.setWidgetResizable(True)
        self.subtask_scroll.setMaximumHeight(220)
        self.subtask_list_host = QWidget()
        self.subtask_list_layout = QVBoxLayout()
        self.subtask_list_layout.setContentsMargins(0, 0, 0, 0)
        self.subtask_list_layout.addStretch(1)
        self.subtask_list_host.setLayout(self.subtask_list_layout)
        self.subtask_scroll.setWidget(self.subtask_list_host)
        v.addWidget(self.subtask_scroll)

        add_row = QHBoxLayout()
        self.subtask_new_edit = QLineEdit()
        self.subtask_new_edit.setPlaceholderText("新子任务内容，回车添加")
        self.subtask_new_edit.returnPressed.connect(self._on_add_subtask_clicked)
        self.subtask_new_edit.textChanged.connect(self._on_subtask_new_text_changed)
        add_row.addWidget(self.subtask_new_edit)
        self.subtask_add_btn = QPushButton("添加")
        self.subtask_add_btn.setEnabled(False)
        self.subtask_add_btn.clicked.connect(self._on_add_subtask_clicked)
        add_row.addWidget(self.subtask_add_btn)
        v.addLayout(add_row)

        group.setLayout(v)
        parent_layout.addWidget(group)

    def _load_subtasks_from_task(self):
        """从 self.task 的 subtasks 字段解析到内存列表（无 task 时清空）。"""
        self._subtasks = []
        if not self.task:
            return
        raw = getattr(self.task, 'subtasks', None) or '[]'
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                parsed = []
        except (ValueError, TypeError):
            parsed = []
        self._subtasks = [
            {
                'id': str(item.get('id') or uuid.uuid4()),
                'title': str(item.get('title', '')),
                'completed': bool(item.get('completed', False)),
            }
            for item in parsed
        ]

    def _on_subtask_new_text_changed(self, text):
        self.subtask_add_btn.setEnabled(bool(text.strip()))

    def _on_add_subtask_clicked(self):
        title = self.subtask_new_edit.text().strip()
        if not title:
            return
        self._subtasks.append({
            "id": str(uuid.uuid4()),
            "title": title,
            "completed": False,
        })
        self.subtask_new_edit.clear()
        self._render_subtasks()
        self.subtask_new_edit.setFocus()

    def _on_delete_subtask_clicked(self, index):
        if 0 <= index < len(self._subtasks):
            del self._subtasks[index]
            self._render_subtasks()

    def _on_subtask_check_changed(self, index, checked):
        if 0 <= index < len(self._subtasks):
            self._subtasks[index]["completed"] = bool(checked)
            self._update_subtask_progress()

    def _on_subtask_title_edited(self, index, text):
        if 0 <= index < len(self._subtasks):
            new_title = text.strip()
            if new_title:
                self._subtasks[index]["title"] = new_title
            else:
                self._render_subtasks()

    def _update_subtask_progress(self):
        total = len(self._subtasks)
        done = sum(1 for s in self._subtasks if s.get("completed"))
        if hasattr(self, "subtask_progress_label"):
            self.subtask_progress_label.setText(f"已完成 {done}/{total}")

    def _render_subtasks(self):
        from PyQt6.QtCore import Qt
        if not hasattr(self, "subtask_list_layout"):
            return
        while self.subtask_list_layout.count() > 1:
            item = self.subtask_list_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        if not self._subtasks:
            empty = QLabel("暂无子任务，点击下方添加")
            empty.setStyleSheet("color: gray;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.subtask_list_layout.insertWidget(0, empty)
        else:
            for idx, item in enumerate(self._subtasks):
                row = QWidget()
                hl = QHBoxLayout()
                hl.setContentsMargins(2, 2, 2, 2)

                cb = QCheckBox()
                cb.setChecked(bool(item.get("completed")))
                cb.stateChanged.connect(
                    lambda state, i=idx: self._on_subtask_check_changed(i, state == Qt.CheckState.Checked.value)
                )
                hl.addWidget(cb)

                edit = QLineEdit(item.get("title", ""))
                edit.editingFinished.connect(
                    lambda i=idx, e=edit: self._on_subtask_title_edited(i, e.text())
                )
                hl.addWidget(edit, 1)

                del_btn = QPushButton("删除")
                del_btn.clicked.connect(lambda _checked=False, i=idx: self._on_delete_subtask_clicked(i))
                hl.addWidget(del_btn)

                row.setLayout(hl)
                self.subtask_list_layout.insertWidget(self.subtask_list_layout.count() - 1, row)

        self._update_subtask_progress()

    def get_task_type_name(self):
        """获取任务类型名称"""
        if self.task_type == TaskType.DAILY:
            return '每日任务'
        elif self.task_type == TaskType.TODO:
            return '待办事项'
        else:
            return '娱乐任务'

    def set_deadline_days(self, days):
        """设置截止日期为几天后"""
        # 获取当前日期并添加指定天数
        current_qdate = self.deadline_date.date()
        # 将QDate转换为Python datetime对象以便计算
        py_date = current_qdate.toPyDate()
        future_date = py_date + timedelta(days=days)

        # 将计算后的日期转换回QDate并设置
        future_qdate = QDate(future_date.year, future_date.month, future_date.day)
        self.deadline_date.setDate(future_qdate)

    def _load_categories(self, task_type: str):
        """加载任务分类到下拉框"""
        self.folder_combo.clear()
        categories = []
        if self.data_manager:
            categories = self.data_manager.get_all_categories(task_type)
        self.folder_combo.addItems(categories)

    def _create_new_category(self, task_type: str):
        """创建新分类"""
        from PyQt6.QtWidgets import QInputDialog
        new_cat, ok = QInputDialog.getText(self, "新建分类", "请输入分类名称:")
        if ok and new_cat.strip():
            new_cat = new_cat.strip()
            if self.data_manager:
                self.data_manager.add_category(new_cat, task_type)
            # 添加到下拉框并选中
            index = self.folder_combo.findText(new_cat)
            if index < 0:
                self.folder_combo.addItem(new_cat)
                index = self.folder_combo.count() - 1
            self.folder_combo.setCurrentIndex(index)

    def load_task_data(self):
        """加载任务数据到表单"""
        if self.task:
            self.title_edit.setText(self.task.title)
            self.desc_edit.setPlainText(self.task.description or '')
            # 设置状态
            status_map = {'pending': '进行中', 'completed': '已完成', 'abandoned': '暂弃'}
            status_text = status_map.get(self.task.status, '进行中')
            index = self.status_combo.findText(status_text)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)

            # 加载标签
            if hasattr(self.task, 'tags') and self.task.tags:
                self.tag_selector.set_selected_tags(self.task.tags)

            if self.task_type == TaskType.DAILY:
                weekday = self.task.week_day if self.task.week_day else '每天'
                index = self.weekday_combo.findText(weekday)
                if index >= 0:
                    self.weekday_combo.setCurrentIndex(index)
                # 加载分类
                if hasattr(self, 'folder_combo') and self.task.category:
                    index = self.folder_combo.findText(self.task.category)
                    if index >= 0:
                        self.folder_combo.setCurrentIndex(index)
            elif self.task_type == TaskType.TODO:
                if self.task.deadline:
                    try:
                        deadline_date = QDate.fromString(self.task.deadline, 'yyyy-MM-dd')
                        self.deadline_date.setDate(deadline_date)
                    except:
                        # 如果解析失败，保持当前日期
                        pass
                else:
                    # 如果没有截止日期，则使用当前日期
                    self.deadline_date.setDate(QDate.currentDate())
                # 加载分类
                if hasattr(self, 'folder_combo') and self.task.category:
                    index = self.folder_combo.findText(self.task.category)
                    if index >= 0:
                        self.folder_combo.setCurrentIndex(index)
            elif self.task_type == TaskType.ENTERTAINMENT:
                index = self.category_combo.findText(self.task.fun_category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
                # 加载分类（复用 category 字段）
                if hasattr(self, 'folder_combo') and self.task.category:
                    index = self.folder_combo.findText(self.task.category)
                    if index >= 0:
                        self.folder_combo.setCurrentIndex(index)

            # 加载子任务（三类任务共用）
            self._load_subtasks_from_task()

            # 加载优先级
            if hasattr(self, 'priority_combo'):
                priority_text = get_priority_label(getattr(self.task, 'priority', DEFAULT_PRIORITY))
                index = self.priority_combo.findText(priority_text)
                if index >= 0:
                    self.priority_combo.setCurrentIndex(index)

            # 加载用时预估
            if hasattr(self, 'duration_spin'):
                duration = getattr(self.task, 'estimated_duration', 0) or 0
                self.duration_spin.setValue(duration)

    def get_data(self):
        """获取表单数据"""
        # 状态映射
        status_map = {'进行中': 'pending', '已完成': 'completed', '暂弃': 'abandoned'}
        status_text = self.status_combo.currentText()
        status_value = status_map.get(status_text, 'pending')
        
        data = {
            'title': self.title_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'completed': status_value == 'completed',
            'status': status_value,
            'tags': self.tag_selector.get_selected_tags()
        }

        if self.task_type == TaskType.DAILY:
            weekday = self.weekday_combo.currentText()
            data['weekday'] = '' if weekday == '每天' else weekday
            data['category'] = self.folder_combo.currentText().strip() if hasattr(self, 'folder_combo') else ''
        elif self.task_type == TaskType.TODO:
            # 获取日期文本而不是直接比较日期对象
            deadline_text = self.deadline_date.text()
            # 如果日期文本是默认的2000年或空，则视为未设置
            if '2000' in deadline_text or not deadline_text.strip() or deadline_text == '2000-01-01':
                data['deadline'] = ''
            else:
                data['deadline'] = self.deadline_date.date().toString('yyyy-MM-dd')
            data['category'] = self.folder_combo.currentText().strip() if hasattr(self, 'folder_combo') else ''
        elif self.task_type == TaskType.ENTERTAINMENT:
            data['fun_category'] = self.category_combo.currentText()
            data['category'] = self.folder_combo.currentText().strip() if hasattr(self, 'folder_combo') else ''

        # 子任务（三类任务共用）
        data['subtasks'] = json.dumps(self._subtasks, ensure_ascii=False)

        # 优先级
        if hasattr(self, 'priority_combo'):
            data['priority'] = LABEL_TO_KEY.get(self.priority_combo.currentText(), DEFAULT_PRIORITY)

        # 用时预估
        if hasattr(self, 'duration_spin'):
            data['estimated_duration'] = self.duration_spin.value()

        return data