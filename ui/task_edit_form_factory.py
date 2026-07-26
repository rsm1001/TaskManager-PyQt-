"""任务编辑对话框字段区工厂。"""

from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QComboBox, QDateEdit, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout

from config.config import ESTIMATED_DURATION_QUICK_OPTIONS
from managers.application.data_manager import TaskType
from managers.tasks.priority import PRIORITY_LABELS

if TYPE_CHECKING:
    from ui.task_edit_dialog import TaskEditDialog


class TaskFieldSectionFactory:
    """按任务类型创建编辑字段，集中处理共用字段。"""

    @classmethod
    def build(cls, dialog: "TaskEditDialog", layout: QVBoxLayout) -> None:
        builders = {
            TaskType.DAILY: cls._build_daily,
            TaskType.TODO: cls._build_todo,
            TaskType.ENTERTAINMENT: cls._build_entertainment,
        }
        builder = builders.get(dialog.task_type)
        if builder is not None:
            builder(dialog, layout)

    @staticmethod
    def _build_daily(dialog: "TaskEditDialog", layout: QVBoxLayout) -> None:
        weekday_layout = QHBoxLayout()
        weekday_layout.addWidget(QLabel("星期:"))
        dialog.weekday_combo = QComboBox()
        dialog.weekday_combo.addItems(["每天", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"])
        weekday_layout.addWidget(dialog.weekday_combo)
        layout.addLayout(weekday_layout)
        TaskFieldSectionFactory._build_folder(dialog, layout, "daily")
        TaskFieldSectionFactory._build_priority_duration_period(dialog, layout)

    @staticmethod
    def _build_todo(dialog: "TaskEditDialog", layout: QVBoxLayout) -> None:
        deadline_layout = QHBoxLayout()
        deadline_layout.addWidget(QLabel("截止日期:"))
        dialog.deadline_date = QDateEdit()
        dialog.deadline_date.setDisplayFormat("yyyy-MM-dd")
        dialog.deadline_date.setCalendarPopup(True)
        dialog.deadline_date.setMinimumDate(QDate.currentDate())
        dialog.deadline_date.setDate(QDate.currentDate())
        deadline_layout.addWidget(dialog.deadline_date)
        layout.addLayout(deadline_layout)

        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("快速设置:"))
        for days, text in ((3, "3天后"), (7, "7天后"), (14, "2周后"), (30, "1个月后"), (60, "2个月后")):
            button = QPushButton(text)
            button.clicked.connect(lambda _checked=False, value=days: dialog.set_deadline_days(value))
            quick_layout.addWidget(button)
        quick_layout.addStretch()
        layout.addLayout(quick_layout)
        TaskFieldSectionFactory._build_folder(dialog, layout, "todo")
        TaskFieldSectionFactory._build_priority_duration_period(dialog, layout)

    @staticmethod
    def _build_entertainment(dialog: "TaskEditDialog", layout: QVBoxLayout) -> None:
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("类别:"))
        dialog.category_combo = QComboBox()
        dialog.category_combo.addItems(["general", "games", "movies", "sports", "reading", "music", "other"])
        category_layout.addWidget(dialog.category_combo)
        layout.addLayout(category_layout)
        TaskFieldSectionFactory._build_folder(dialog, layout, "entertainment")
        TaskFieldSectionFactory._build_priority_duration_period(dialog, layout)

    @staticmethod
    def _build_folder(dialog: "TaskEditDialog", layout: QVBoxLayout, task_type: str) -> None:
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("分类:"))
        dialog.folder_combo = QComboBox()
        dialog.folder_combo.setEditable(True)
        dialog.folder_combo.setMinimumWidth(150)
        dialog._load_categories(task_type)
        folder_layout.addWidget(dialog.folder_combo)
        button = QPushButton("新建")
        button.clicked.connect(lambda _checked=False: dialog._create_new_category(task_type))
        folder_layout.addWidget(button)
        layout.addLayout(folder_layout)

    @staticmethod
    def _build_priority_duration_period(dialog: "TaskEditDialog", layout: QVBoxLayout) -> None:
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("优先级:"))
        dialog.priority_combo = QComboBox()
        dialog.priority_combo.addItems(PRIORITY_LABELS)
        priority_layout.addWidget(dialog.priority_combo)
        priority_layout.addStretch()
        layout.addLayout(priority_layout)

        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("用时预估:"))
        dialog.duration_spin = QSpinBox()
        dialog.duration_spin.setRange(0, 999)
        dialog.duration_spin.setSuffix(" 分钟")
        dialog.duration_spin.setValue(0)
        duration_layout.addWidget(dialog.duration_spin)
        for minutes in ESTIMATED_DURATION_QUICK_OPTIONS:
            button = QPushButton(f"{minutes}分钟")
            button.setMinimumWidth(60)
            button.clicked.connect(lambda _checked=False, value=minutes: dialog.duration_spin.setValue(value))
            duration_layout.addWidget(button)
        duration_layout.addStretch()
        layout.addLayout(duration_layout)

        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("时段:"))
        dialog.period_combo = QComboBox()
        dialog._populate_period_combo()
        period_layout.addWidget(dialog.period_combo, 1)
        button = QPushButton("刷新")
        button.clicked.connect(dialog._populate_period_combo)
        period_layout.addWidget(button)
        layout.addLayout(period_layout)
