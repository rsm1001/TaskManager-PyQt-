"""任务编辑对话框的协调层。"""

import logging
from datetime import timedelta

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from managers.application.data_manager import TaskType
from ui.task_edit_data_mapper import TaskEditDataMapper
from ui.task_edit_form_factory import TaskFieldSectionFactory
from ui.task_edit_subtasks import SubtaskEditor
from utils.log_context import get_trace_id
from widgets.tag_selector_widget import TagSelectorWidget


logger = logging.getLogger(__name__)


class TaskEditDialog(QDialog):
    """协调任务字段工厂、子任务组件和数据映射器。"""

    def __init__(self, task_type: TaskType, parent=None, task=None, data_manager=None):
        super().__init__(parent)
        self.task_type = task_type
        self.task = task
        self.data_manager = data_manager
        self._period_userdata_map = {}
        self._init_ui()
        if task:
            self.load_task_data()

    def _init_ui(self) -> None:
        self.setWindowTitle(f"{'编辑' if self.task else '添加'}{self.get_task_type_name()}")
        self.setModal(True)
        self.resize(560, 620)
        layout = QVBoxLayout(self)
        self._build_base_fields(layout)
        TaskFieldSectionFactory.build(self, layout)
        self.subtask_editor = SubtaskEditor(self)
        layout.addWidget(self.subtask_editor)
        self._build_status_and_actions(layout)

    def _build_base_fields(self, layout: QVBoxLayout) -> None:
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        self.title_edit = QLineEdit()
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)
        layout.addWidget(QLabel("描述:"))
        self.desc_edit = QTextEdit()
        layout.addWidget(self.desc_edit)
        self.tag_selector = TagSelectorWidget(
            parent=self,
            data_manager=self.data_manager,
            initial_tags=self.task.tags if self.task else "",
            task_type=self.task_type,
        )
        layout.addWidget(self.tag_selector)

    def _build_status_and_actions(self, layout: QVBoxLayout) -> None:
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["进行中", "已完成", "暂弃"])
        status_layout.addWidget(self.status_combo)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        actions = QHBoxLayout()
        actions.addStretch()
        confirm = QPushButton("确定")
        confirm.clicked.connect(self.accept)
        actions.addWidget(confirm)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        layout.addLayout(actions)

    def get_task_type_name(self) -> str:
        names = {
            TaskType.DAILY: "每日任务",
            TaskType.TODO: "待办事项",
            TaskType.ENTERTAINMENT: "娱乐任务",
        }
        return names.get(self.task_type, "娱乐任务")

    def set_deadline_days(self, days: int) -> None:
        date = self.deadline_date.date().toPyDate() + timedelta(days=days)
        self.deadline_date.setDate(QDate(date.year, date.month, date.day))

    def _load_categories(self, task_type: str) -> None:
        self.folder_combo.clear()
        if self.data_manager is not None:
            self.folder_combo.addItems(self.data_manager.get_all_categories(task_type))

    def _create_new_category(self, task_type: str) -> None:
        category, accepted = QInputDialog.getText(self, "新建分类", "请输入分类名称:")
        category = category.strip()
        if not accepted or not category:
            return
        if self.data_manager is not None:
            self.data_manager.add_category(category, task_type)
        index = self.folder_combo.findText(category)
        if index < 0:
            self.folder_combo.addItem(category)
            index = self.folder_combo.count() - 1
        self.folder_combo.setCurrentIndex(index)
        logger.info("创建任务分类 trace_id=%s task_type=%s", get_trace_id(), task_type)

    def _populate_period_combo(self) -> None:
        if not hasattr(self, "period_combo"):
            return
        current_id = self.period_combo.currentData()
        self.period_combo.blockSignals(True)
        self.period_combo.clear()
        self._period_userdata_map = {"未设时段": ""}
        self.period_combo.addItem("未设时段", "")
        if self.data_manager is not None:
            try:
                for period in self.data_manager.get_all_time_periods():
                    self.period_combo.addItem(period.name, period.id)
                    self._period_userdata_map[period.name] = period.id
            except Exception:
                logger.exception("加载任务时段失败 trace_id=%s", get_trace_id())
        for index in range(self.period_combo.count()):
            if self.period_combo.itemData(index) == current_id:
                self.period_combo.setCurrentIndex(index)
                break
        self.period_combo.blockSignals(False)

    def load_task_data(self) -> None:
        """将待编辑任务映射至表单。"""
        TaskEditDataMapper.load(self)

    def get_data(self) -> dict:
        """返回与原调用方兼容的任务数据字典。"""
        return TaskEditDataMapper.to_dict(self)

    def accept(self) -> None:
        logger.info("确认任务编辑 trace_id=%s task_type=%s", get_trace_id(), self.task_type.value)
        super().accept()
