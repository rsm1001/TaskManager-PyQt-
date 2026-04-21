"""
Task Manager - 任务编辑对话框模块
将原来的 TaskEditDialog 类从 main.py 中分离出来以实现解耦
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTextEdit, 
                             QLabel, QComboBox, QCheckBox, QDateEdit, QPushButton, QGridLayout)
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox
from managers.data_manager import TaskType
from datetime import timedelta
import datetime
import uuid


class TaskEditDialog(QDialog):
    """任务编辑对话框"""

    def __init__(self, task_type: TaskType, parent=None, task=None):
        super().__init__(parent)
        self.task_type = task_type
        self.task = task
        self.init_ui()
        if task:
            self.load_task_data()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"{'编辑' if self.task else '添加'}{self.get_task_type_name()}")
        self.setModal(True)
        self.resize(500, 400)

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

        # 任务特定字段
        if self.task_type == TaskType.DAILY:
            weekday_layout = QHBoxLayout()
            weekday_layout.addWidget(QLabel('星期:'))
            self.weekday_combo = QComboBox()
            self.weekday_combo.addItems(['每天', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'])
            weekday_layout.addWidget(self.weekday_combo)
            layout.addLayout(weekday_layout)
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
        elif self.task_type == TaskType.ENTERTAINMENT:
            category_layout = QHBoxLayout()
            category_layout.addWidget(QLabel('类别:'))
            self.category_combo = QComboBox()
            self.category_combo.addItems(['general', 'games', 'movies', 'sports', 'reading', 'music', 'other'])
            category_layout.addWidget(self.category_combo)
            layout.addLayout(category_layout)

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

            if self.task_type == TaskType.DAILY:
                weekday = self.task.week_day if self.task.week_day else '每天'
                index = self.weekday_combo.findText(weekday)
                if index >= 0:
                    self.weekday_combo.setCurrentIndex(index)
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
            elif self.task_type == TaskType.ENTERTAINMENT:
                index = self.category_combo.findText(self.task.fun_category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)

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
            'status': status_value
        }

        if self.task_type == TaskType.DAILY:
            weekday = self.weekday_combo.currentText()
            data['weekday'] = '' if weekday == '每天' else weekday
        elif self.task_type == TaskType.TODO:
            # 获取日期文本而不是直接比较日期对象
            deadline_text = self.deadline_date.text()
            # 如果日期文本是默认的2000年或空，则视为未设置
            if '2000' in deadline_text or not deadline_text.strip() or deadline_text == '2000-01-01':
                data['deadline'] = ''
            else:
                data['deadline'] = self.deadline_date.date().toString('yyyy-MM-dd')
        elif self.task_type == TaskType.ENTERTAINMENT:
            data['fun_category'] = self.category_combo.currentText()

        return data