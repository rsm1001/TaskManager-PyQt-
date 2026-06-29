"""
时段设置对话框 - 时段的智能点选与重命名 / 单删 / 批量删除
- 「新增」/「编辑」走编辑对话框，顶部为 6 段标准时段芯片（一键填名称/起止/颜色）
  起止时间使用 QTimeEdit：可点开日历式时钟面板快速选几点几分，也可直接键入
- 「批量删除」支持多选后一次删多个（每个独立联动清引用）
- 不再有「智能添加」一键批量补齐；6 段芯片仅作为新增/编辑时的快选模板
- 任务类工具统一聚类，外部入口见 components/ui_elements.py
"""
import logging
import re
from typing import List, Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QColorDialog,
    QLineEdit, QFormLayout, QGroupBox, QFrame,
    QAbstractItemView, QTimeEdit, QAbstractSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTime
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


# 6 段默认时段芯片（仅作为新增/编辑时的快速模板；不会自动批量写入数据库）
DEFAULT_TIME_PERIODS = [
    # (name, start, end, color)
    ("早起",  "05:00", "07:00", "#FFE0B2"),
    ("上午",  "07:00", "12:00", "#E3F2FD"),
    ("中午",  "12:00", "14:00", "#FFF59D"),
    ("下午",  "14:00", "18:00", "#C8E6C9"),
    ("晚上",  "18:00", "23:00", "#D1C4E9"),
    ("深夜",  "23:00", "05:00", "#ECEFF1"),
]


class SmartChipBar(QFrame):
    """6 段默认时段芯片行：点一下联动表单一键填名称/起止/颜色"""

    chipClicked = pyqtSignal(str, str, str, str)

    def __init__(self, parent=None, exclude_names: Optional[List[str]] = None):
        super().__init__(parent)
        self._exclude = set(exclude_names or [])
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for name, start, end, color in DEFAULT_TIME_PERIODS:
            already = name in self._exclude
            btn = QPushButton(f"{name}  {start}~{end}")
            btn.setMinimumHeight(28)
            tip_suffix = "（已存在，将覆盖名称/起止）" if already else ""
            btn.setToolTip(f"一键填入：{name} {start}~{end}（{color}）{tip_suffix}")
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {color}; color: #333; "
                f"border: 1px solid #bdbdbd; border-radius: 12px; padding: 2px 10px; }}"
                f"QPushButton:hover {{ border-color: #1976D2; }}"
            )
            btn.clicked.connect(
                lambda _checked=False, n=name, s=start, e=end, c=color: self.chipClicked.emit(n, s, e, c)
            )
            layout.addWidget(btn)
        layout.addStretch()


class WrappingQTimeEdit(QTimeEdit):
    """QTimeEdit 子类：时分上下调节触到边界时自动环绕

    QAbstractSpinBox 默认在 min/max 处禁用对应方向的 spin button，
    所以光重写 stepBy 还不够——边界时的"↡"会被灰掉，stepBy 根本不会被调。
    这里一并覆盖 stepEnabled 让两个按钮始终可点，再由 stepBy 完成环绕。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # 不限制 min/max；不设 specialValueText，避免 00:00 被显示成空白
        self.setDisplayFormat("HH:mm")
        self.setCalendarPopup(True)

    def stepEnabled(self):  # type: ignore[override]
        """始终让 ↥/↧ 可点（不管是否到边界），否则 00:00 时下滑键灰掉无法触发 stepBy"""
        return QAbstractSpinBox.StepEnabledFlag.StepUpEnabled | QAbstractSpinBox.StepEnabledFlag.StepDownEnabled

    def stepBy(self, steps):  # type: ignore[override]
        """时分节循环加减

        覆盖 QAbstractSpinBox.stepBy；同时兼容键盘 ↑/↓、箭头点击、鼠标滚轮
        以及程序调用 stepUp()/stepDown()。
        """
        cur_section = self.currentSection()
        t = self.time()
        new_hour = t.hour()
        new_minute = t.minute()
        section_changed = False
        if cur_section == QTimeEdit.Section.HourSection:
            new_hour = self._wrap(t.hour(), steps, 24)
            section_changed = True
        elif cur_section == QTimeEdit.Section.MinuteSection:
            new_minute = self._wrap(t.minute(), steps, 60)
            section_changed = True
        if not section_changed:
            return
        if new_hour == t.hour() and new_minute == t.minute():
            return
        self.setTime(QTime(new_hour, new_minute))

    @staticmethod
    def _wrap(cur: int, steps: int, modulo: int) -> int:
        """cur 上加 steps 后按 modulo 循环（支持负 steps 与绝对值 >1 的 wheel）"""
        n = (cur + steps) % modulo
        if n < 0:
            n += modulo
        return n


def _parse_hhmm(text: str) -> Optional[QTime]:
    """把 HH:MM 字符串解析为 QTime；解析失败返回 None"""
    if not text:
        return None
    try:
        h, m = text.split(":", 1)
        t = QTime(int(h), int(m))
        if not t.isValid():
            return None
        return t
    except (ValueError, AttributeError):
        return None


def _qtime_to_str(t: QTime) -> str:
    """QTime 安全转字符串（用于数据库存储）"""
    if t is None or not t.isValid():
        return ""
    return t.toString("HH:mm")


class TimePeriodEditDialog(QDialog):
    """新增/编辑单个时段

    - 顶部为 6 段默认时段芯片，点一下自动填名称/起止/颜色
    - 起止时间用 QTimeEdit：可点开日历式时钟面板，也可直接键入
    - 下方仍可手工覆盖任何字段再保存
    """

    def __init__(self, parent=None, title: str = "新增时段",
                 default_name: str = "",
                 default_start: str = "",
                 default_end: str = "",
                 default_color: str = "",
                 exclude_names: Optional[List[str]] = None):
        super().__init__(parent)
        self._color = default_color
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(380)
        self._build_ui(default_name, default_start, default_end, default_color, exclude_names)

    def _build_ui(self, name: str, start: str, end: str, color: str,
                  exclude_names: Optional[List[str]]):
        layout = QVBoxLayout(self)

        # 智能点选芯片（仅用于模板填充，不再自动批量写库）
        chip_group = QGroupBox("智能点选（点一下自动填名称/起止/颜色）")
        chip_layout = QVBoxLayout(chip_group)
        chip_bar = SmartChipBar(self, exclude_names=exclude_names)
        chip_bar.chipClicked.connect(self._apply_chip)
        chip_layout.addWidget(chip_bar)
        layout.addWidget(chip_group)

        # 手动编辑区
        form_group = QGroupBox("手动编辑")
        form = QFormLayout(form_group)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("如：早晨 / 上午 / 下午 / 晚上")
        form.addRow("名称:", self.name_edit)

        time_row = QHBoxLayout()
        # 起止时间改用 WrappingQTimeEdit：支持日历式时钟面板 + 直接键入
        # 且时分上下调节/滑轮会循环（01→00→23，30→29→00→59 等）
        self.start_edit = WrappingQTimeEdit()
        parsed_start = _parse_hhmm(start)
        self.start_edit.setTime(parsed_start if parsed_start else QTime(0, 0))

        self.end_edit = WrappingQTimeEdit()
        parsed_end = _parse_hhmm(end)
        self.end_edit.setTime(parsed_end if parsed_end else QTime(0, 0))

        time_row.addWidget(self.start_edit)
        time_row.addWidget(QLabel("至"))
        time_row.addWidget(self.end_edit)
        time_row.addStretch()
        form.addRow("起止时间（可选）:", time_row)

        self.color_btn = QPushButton("选择颜色…")
        self.color_btn.clicked.connect(self._pick_color)
        if color:
            self.color_btn.setStyleSheet(self._swatch_style(color))
        self._color = color
        form.addRow("颜色（可选）:", self.color_btn)

        layout.addWidget(form_group)

        hint = QLabel(
            "提示：起止时间点右侧 ⌄ 弹出日历式时钟面板，亦可直接键入 HH:MM。\n"
            "名称修改后，已绑定该时段的任务显示文本会跟随更新。"
        )
        hint.setStyleSheet("color: gray; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        ok_btn.setDefault(True)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _apply_chip(self, name: str, start: str, end: str, color: str):
        """智能芯片被点：把名称/起止/颜色一键写回表单"""
        self.name_edit.setText(name)
        parsed_start = _parse_hhmm(start)
        if parsed_start:
            self.start_edit.setTime(parsed_start)
        parsed_end = _parse_hhmm(end)
        if parsed_end:
            self.end_edit.setTime(parsed_end)
        self._color = color
        self.color_btn.setStyleSheet(self._swatch_style(color))

    def _pick_color(self):
        color = QColorDialog.getColor(
            QColor(self._color) if self._color else QColor("#FFA726"),
            self, "选择颜色"
        )
        if color.isValid():
            self._color = color.name()
            self.color_btn.setStyleSheet(self._swatch_style(self._color))

    def _swatch_style(self, hex_color: str) -> str:
        return f"QPushButton {{ background-color: {hex_color}; color: white; }}"

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "时段名称不能为空。")
            return
        start_qtime = self.start_edit.time()
        end_qtime = self.end_edit.time()
        # HH:MM 校验（00:00 也是合法的）
        hhmm = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        start_str = _qtime_to_str(start_qtime)
        end_str = _qtime_to_str(end_qtime)
        if start_str and not hhmm.match(start_str):
            QMessageBox.warning(self, "提示", "起始时间格式应为 HH:MM（如 08:00）")
            return
        if end_str and not hhmm.match(end_str):
            QMessageBox.warning(self, "提示", "结束时间格式应为 HH:MM（如 12:00）")
            return
        self.accept()

    def get_result(self) -> Tuple[str, str, str, str]:
        return (
            self.name_edit.text().strip(),
            _qtime_to_str(self.start_edit.time()),
            _qtime_to_str(self.end_edit.time()),
            self._color or "",
        )


class TimePeriodDialog(QDialog):
    """时段设置对话框（新增 / 重命名 / 单删 / 批量删除 / 重排）

    - 多选时段后点「批量删除」一次删除多个
    - 「新增」「编辑」走编辑对话框，含 6 段芯片（点一下自动填名称/起止/颜色）
    - 「删除」仅删除当前选中那一个
    """

    updated = pyqtSignal()

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self._dm = data_manager
        self.setWindowTitle("时段设置")
        self.setModal(True)
        self.resize(520, 500)
        self._build_ui()
        self._reload_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        info = QLabel(
            "「新增」/「编辑」打开对话框，顶部 6 段芯片可一键填名称/起止/颜色，亦可手写。\n"
            "「删除」仅删除当前选中的一个；按住 Ctrl/Shift 多选后用「批量删除」一次删多个。\n"
            "删除会清空引用任务上的时段显示（任务本身保留）。"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("新增")
        add_btn.setToolTip("打开新增对话框，里面有 6 段芯片可一键填也可手写")
        add_btn.clicked.connect(self._on_add)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self._on_edit)
        del_btn = QPushButton("删除")
        del_btn.setToolTip("仅删除当前选中那一个时段")
        del_btn.clicked.connect(self._on_delete)
        batch_del_btn = QPushButton("批量删除")
        batch_del_btn.setToolTip("Ctrl/Shift 多选后，一次性删除所选时段（每个独立联动清引用）")
        batch_del_btn.clicked.connect(self._on_batch_delete)
        up_btn = QPushButton("上移")
        up_btn.clicked.connect(lambda: self._on_move(-1))
        down_btn = QPushButton("下移")
        down_btn.clicked.connect(lambda: self._on_move(1))
        for b in (add_btn, edit_btn, del_btn, batch_del_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        layout.addLayout(btn_row)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _reload_list(self):
        self.list_widget.clear()
        if not self._dm:
            return
        for period in self._dm.get_all_time_periods():
            display = self._format_display(period)
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, period.id)
            tip_parts = []
            if period.start_time or period.end_time:
                tip_parts.append(f"{period.start_time or '--:--'} ~ {period.end_time or '--:--'}")
            if period.color:
                tip_parts.append(period.color)
            if tip_parts:
                item.setToolTip("  ".join(tip_parts))
            if period.color:
                item.setBackground(QColor(period.color))
                item.setForeground(QColor("white"))
            self.list_widget.addItem(item)

    @staticmethod
    def _format_display(period) -> str:
        bits = [period.name]
        if period.start_time or period.end_time:
            bits.append(f"{period.start_time or '--:--'}~{period.end_time or '--:--'}")
        return "  ".join(bits)

    def _selected_period_ids(self) -> List[str]:
        """当前列表选中项对应的 period_id 列表（顺序与点击一致）"""
        ids: List[str] = []
        for item in self.list_widget.selectedItems():
            pid = item.data(Qt.ItemDataRole.UserRole)
            if pid:
                ids.append(pid)
        return ids

    def _existing_names(self, exclude_id: Optional[str] = None) -> List[str]:
        return [
            p.name for p in self._dm.get_all_time_periods()
            if p.id != exclude_id
        ] if self._dm else []

    def _on_add(self):
        if not self._dm:
            return
        dlg = TimePeriodEditDialog(
            self, title="新增时段",
            exclude_names=self._existing_names(),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, start, end, color = dlg.get_result()
        if name in self._existing_names():
            QMessageBox.warning(self, "提示", f"已存在同名时段：{name}")
            return
        self._dm.create_time_period(name=name, start_time=start, end_time=end, color=color)
        self._reload_list()
        self.updated.emit()
        logger.info("新增时段 name=%s", name)

    def _on_edit(self):
        selected = self._selected_period_ids()
        if len(selected) != 1:
            QMessageBox.information(self, "提示", "请仅选择一个时段进行编辑（编辑不允许批量）")
            return
        period = self._dm.get_time_period_by_id(selected[0])
        if not period:
            QMessageBox.information(self, "提示", "请先在列表中选择一个时段")
            return
        dlg = TimePeriodEditDialog(
            self, title="编辑时段",
            default_name=period.name,
            default_start=period.start_time or "",
            default_end=period.end_time or "",
            default_color=period.color or "",
            exclude_names=self._existing_names(exclude_id=period.id),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, start, end, color = dlg.get_result()
        others = self._existing_names(exclude_id=period.id)
        if name in others:
            QMessageBox.warning(self, "提示", f"已存在同名时段：{name}")
            return
        self._dm.update_time_period(
            period.id, name=name, start_time=start, end_time=end, color=color
        )
        self._reload_list()
        self.updated.emit()
        logger.info("编辑时段 id=%s new_name=%s", period.id, name)

    def _on_delete(self):
        """删除单选中的时段"""
        selected = self._selected_period_ids()
        if len(selected) != 1:
            QMessageBox.information(self, "提示", "「删除」只删除选中那一个；多选用「批量删除」")
            return
        self._delete_by_ids(selected)

    def _on_batch_delete(self):
        """批量删除所有选中时段"""
        selected = self._selected_period_ids()
        if not selected:
            QMessageBox.information(self, "提示", "请先在列表中选择要批量删除的时段（可按 Ctrl/Shift 多选）")
            return
        if len(selected) == 1:
            # 单选直接走单删路径，提示更友好
            self._delete_by_ids(selected)
            return
        names = [p.name for p in self._dm.get_all_time_periods() if p.id in selected]
        reply = QMessageBox.question(
            self, "批量删除确认",
            f"将删除以下 {len(selected)} 个时段：\n" + "、".join(names) + "\n\n"
            "引用这些时段的任务时段显示将变为「未设时段」（任务本身保留），继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._delete_by_ids(selected)

    def _delete_by_ids(self, ids: List[str]):
        """实际执行删除，每个独立联动清引用并刷新 UI 一次"""
        for pid in ids:
            self._dm.delete_time_period(pid)
        self._reload_list()
        self.updated.emit()
        logger.info("删除时段 | ids=%s", ids)

    def _on_move(self, delta: int):
        periods = list(self._dm.get_all_time_periods())
        periods.sort(key=lambda p: (p.order_index or 0, p.name or ""))
        ids = [p.id for p in periods]

        # 若多选，移动整个选中组
        selected = self._selected_period_ids()
        # 若用户单选了一个，且按上下移则移动单个；否则按当前顺序整体移动第一个
        if not selected:
            return
        if len(selected) == 1:
            current_id = selected[0]
            if current_id not in ids:
                return
            idx = ids.index(current_id)
            new_idx = idx + delta
            if new_idx < 0 or new_idx >= len(ids):
                return
            ids.pop(idx)
            ids.insert(new_idx, current_id)
        else:
            current_id = selected[0]
            if current_id not in ids:
                return
            idx = ids.index(current_id)
            new_idx = idx + delta
            if new_idx < 0 or new_idx >= len(ids):
                return
            # 简化：多选时只移动首个
            ids.pop(idx)
            ids.insert(new_idx, current_id)
        self._dm.time_period_orchestrator.reorder(ids)
        self._reload_list()
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == current_id:
                self.list_widget.setCurrentRow(i)
                break
        self.updated.emit()
