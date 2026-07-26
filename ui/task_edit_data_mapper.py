"""任务编辑表单与任务实体之间的数据映射。"""

import logging
from typing import TYPE_CHECKING, Dict

from PyQt6.QtCore import QDate

from managers.application.data_manager import TaskType
from managers.tasks.priority import DEFAULT_PRIORITY, LABEL_TO_KEY, get_priority_label
from utils.log_context import get_trace_id

if TYPE_CHECKING:
    from ui.task_edit_dialog import TaskEditDialog


logger = logging.getLogger(__name__)

STATUS_TO_TEXT = {"pending": "进行中", "completed": "已完成", "abandoned": "暂弃"}
TEXT_TO_STATUS = {value: key for key, value in STATUS_TO_TEXT.items()}


class TaskEditDataMapper:
    """隔离 UI 字段与任务实体字段的转换规则。"""

    @classmethod
    def load(cls, dialog: "TaskEditDialog") -> None:
        task = dialog.task
        if task is None:
            return
        dialog.title_edit.setText(task.title)
        dialog.desc_edit.setPlainText(task.description or "")
        cls._select_text(dialog.status_combo, STATUS_TO_TEXT.get(task.status, "进行中"))
        if getattr(task, "tags", None):
            dialog.tag_selector.set_selected_tags(task.tags)
        cls._load_type_specific_fields(dialog)
        dialog.subtask_editor.load_serialized(getattr(task, "subtasks", None) or "[]")
        if hasattr(dialog, "priority_combo"):
            cls._select_text(
                dialog.priority_combo,
                get_priority_label(getattr(task, "priority", DEFAULT_PRIORITY)),
            )
        if hasattr(dialog, "duration_spin"):
            dialog.duration_spin.setValue(getattr(task, "estimated_duration", 0) or 0)
        if hasattr(dialog, "period_combo"):
            dialog._populate_period_combo()
            cls._select_period(dialog, getattr(task, "time_period_id", None) or "")
        logger.info("加载任务编辑数据 trace_id=%s task_type=%s", get_trace_id(), dialog.task_type.value)

    @classmethod
    def to_dict(cls, dialog: "TaskEditDialog") -> Dict[str, object]:
        status = TEXT_TO_STATUS.get(dialog.status_combo.currentText(), "pending")
        data: Dict[str, object] = {
            "title": dialog.title_edit.text().strip(),
            "description": dialog.desc_edit.toPlainText().strip(),
            "completed": status == "completed",
            "status": status,
            "tags": dialog.tag_selector.get_selected_tags(),
            "subtasks": dialog.subtask_editor.to_serialized(),
        }
        if hasattr(dialog, "priority_combo"):
            data["priority"] = LABEL_TO_KEY.get(dialog.priority_combo.currentText(), DEFAULT_PRIORITY)
        if hasattr(dialog, "duration_spin"):
            data["estimated_duration"] = dialog.duration_spin.value()
        if hasattr(dialog, "period_combo"):
            data["time_period_id"] = dialog.period_combo.itemData(dialog.period_combo.currentIndex()) or ""
        if dialog.task_type == TaskType.DAILY:
            weekday = dialog.weekday_combo.currentText()
            data.update({"weekday": "" if weekday == "每天" else weekday, "category": dialog.folder_combo.currentText().strip()})
        elif dialog.task_type == TaskType.TODO:
            deadline_text = dialog.deadline_date.text()
            data.update({
                "deadline": "" if "2000" in deadline_text or not deadline_text.strip() else dialog.deadline_date.date().toString("yyyy-MM-dd"),
                "category": dialog.folder_combo.currentText().strip(),
            })
        elif dialog.task_type == TaskType.ENTERTAINMENT:
            data.update({"fun_category": dialog.category_combo.currentText(), "category": dialog.folder_combo.currentText().strip()})
        logger.info("收集任务编辑数据 trace_id=%s task_type=%s", get_trace_id(), dialog.task_type.value)
        return data

    @staticmethod
    def _load_type_specific_fields(dialog: "TaskEditDialog") -> None:
        task = dialog.task
        if dialog.task_type == TaskType.DAILY:
            TaskEditDataMapper._select_text(dialog.weekday_combo, task.week_day or "每天")
        elif dialog.task_type == TaskType.TODO:
            if task.deadline:
                deadline = QDate.fromString(task.deadline, "yyyy-MM-dd")
                if deadline.isValid():
                    dialog.deadline_date.setDate(deadline)
            else:
                dialog.deadline_date.setDate(QDate.currentDate())
        elif dialog.task_type == TaskType.ENTERTAINMENT:
            TaskEditDataMapper._select_text(dialog.category_combo, task.fun_category)
        if getattr(task, "category", None) and hasattr(dialog, "folder_combo"):
            TaskEditDataMapper._select_text(dialog.folder_combo, task.category)

    @staticmethod
    def _select_text(combo, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _select_period(dialog: "TaskEditDialog", period_id: str) -> None:
        for index in range(dialog.period_combo.count()):
            if dialog.period_combo.itemData(index) == period_id:
                dialog.period_combo.setCurrentIndex(index)
                return
