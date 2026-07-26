"""行程的时段块和日视图组件。"""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QStyle, QVBoxLayout, QWidget

from components.itinerary.constants import BLOCK_COLORS, BLOCK_HEADER_HEIGHT, HOUR_BLOCKS, WEEKDAY_FULL
from components.itinerary.factory import ItineraryComponentFactory


class HourBlockWidget(QFrame):
    """管理四个小时槽的可折叠时段块。"""

    task_dropped = pyqtSignal(str, str, int, int)

    def __init__(self, start_hour, block_name, day_index, data_manager=None, main_window=None, parent=None):
        super().__init__(parent)
        self.start_hour, self.block_name, self.day_index = start_hour, block_name, day_index
        self.data_manager, self.main_window = data_manager, main_window
        self.collapsed, self.hour_slots = True, []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        color = BLOCK_COLORS.get(self.block_name, '#3498DB')
        header_box = QPushButton()
        header_box.setFixedHeight(BLOCK_HEADER_HEIGHT)
        header_box.clicked.connect(self._toggle_collapse)
        header_box.setStyleSheet(f'QPushButton {{ background-color: {color}; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {color}DD; }}')
        header = QHBoxLayout(header_box)
        header.setContentsMargins(0, 0, 0, 0)
        self.header = QPushButton()
        self.header.clicked.connect(self._toggle_collapse)
        self.header.setStyleSheet(f'QPushButton {{ background-color: transparent; color: white; border: none; font-size: 13px; font-weight: bold; text-align: left; padding-left: 10px; }} QPushButton:hover {{ background-color: {color}DD; }}')
        header.addWidget(self.header)
        for standard_icon, tip, handler in [
            (QStyle.StandardPixmap.SP_BrowserReload, '移除本时段未完成任务', self._remove_unfinished),
            (QStyle.StandardPixmap.SP_TrashIcon, '移除本时段全部任务', self._remove_all),
        ]:
            button = QPushButton()
            button.setFixedSize(28, BLOCK_HEADER_HEIGHT)
            button.setIcon(self.style().standardIcon(standard_icon))
            button.setIconSize(QSize(16, 16))
            button.setToolTip(tip)
            button.clicked.connect(handler)
            button.setStyleSheet('QPushButton { background: transparent; color: white; border: none; font-size: 14px; } QPushButton:hover { background-color: #E74C3C; border-radius: 4px; }')
            header.addWidget(button)
        layout.addWidget(header_box)
        self.slots_container = QWidget()
        slots = QVBoxLayout(self.slots_container)
        slots.setContentsMargins(4, 4, 4, 4)
        slots.setSpacing(3)
        for hour in range(self.start_hour, self.start_hour + 4):
            slot = ItineraryComponentFactory.create_hour_slot(hour, self.day_index, self.data_manager, self.main_window)
            slot.task_dropped.connect(self._on_slot_task_dropped)
            self.hour_slots.append(slot)
            slots.addWidget(slot)
        layout.addWidget(self.slots_container)
        self.slots_container.setVisible(False)
        self._update_header()

    def _on_slot_task_dropped(self, task_id, task_type, _day, hour):
        self.task_dropped.emit(task_id, task_type, 0, hour)

    def _toggle_collapse(self):
        self.collapsed = not self.collapsed
        self.slots_container.setVisible(not self.collapsed)
        self._update_header()

    def _update_header(self):
        self.header.setText(f"{'▸' if self.collapsed else '▾'} {self.block_name} ({self.start_hour:02d}:00-{self.start_hour + 4:02d}:00)")

    def _remove_unfinished(self):
        for slot in self.hour_slots:
            slot._remove_unfinished()

    def _remove_all(self):
        for slot in self.hour_slots:
            slot.clear_all()

    def get_slot(self, hour):
        return next((slot for slot in self.hour_slots if slot.hour == hour), None)


class DayViewWidget(QWidget):
    """组合一天中各时段的视图。"""

    task_dropped = pyqtSignal(str, str, int, int)

    def __init__(self, day_index, data_manager=None, main_window=None, parent=None):
        super().__init__(parent)
        self.day_index, self.data_manager, self.main_window = day_index, data_manager, main_window
        self.blocks = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        title = QLabel(WEEKDAY_FULL[self.day_index])
        title.setStyleSheet('font-size: 16px; font-weight: bold; color: #2C3E50;')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        blocks = QVBoxLayout(container)
        blocks.setContentsMargins(0, 0, 0, 0)
        blocks.setSpacing(4)
        for start_hour, block_name in HOUR_BLOCKS:
            block = ItineraryComponentFactory.create_hour_block(start_hour, block_name, self.day_index, self.data_manager, self.main_window)
            block.task_dropped.connect(self._on_task_dropped)
            self.blocks.append(block)
            blocks.addWidget(block)
        blocks.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_task_dropped(self, task_id, task_type, _day, hour):
        self.task_dropped.emit(task_id, task_type, self.day_index, hour)

    def get_slot(self, hour):
        for block in self.blocks:
            slot = block.get_slot(hour)
            if slot:
                return slot
        return None

    def clear_all(self):
        for block in self.blocks:
            block._remove_all()
