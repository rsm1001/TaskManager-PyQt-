"""
Pomodoro Toolbar Widget - 番茄钟浮动工具栏
悬浮在主窗口角落的计时器显示
"""

import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QPoint
from PyQt6.QtGui import QFont, QPalette, QColor, QMouseEvent

logger = logging.getLogger(__name__)


class PomodoroToolbarWidget(QWidget):
    """番茄钟浮动工具栏"""

    def __init__(self, pomodoro_service, parent=None):
        super().__init__(parent)
        self._service = pomodoro_service
        self._is_attached = False
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("番茄钟")
        self.setFixedWidth(280)
        self.setFixedHeight(180)
        self.setWindowFlags(Qt.WindowType.Tool |
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._dragging = False
        self._drag_position = QPoint()
        self.setStyleSheet("""
            PomodoroToolbarWidget {
                background-color: #2C3E50;
                border-radius: 10px;
                border: 1px solid #34495E;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 标题栏（可拖动）
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("🍅 番茄钟"))
        title_layout.addStretch()

        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFixedSize(20, 20)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ECF0F1;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #34495E;
                border-radius: 3px;
            }
        """)
        self.minimize_btn.clicked.connect(self.hide)
        title_layout.addWidget(self.minimize_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ECF0F1;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #E74C3C;
                border-radius: 3px;
            }
        """)
        self.close_btn.clicked.connect(self._on_close)
        title_layout.addWidget(self.close_btn)
        layout.addLayout(title_layout)

        # 任务名称
        self.task_label = QLabel("未选择任务")
        self.task_label.setStyleSheet("color: #BDC3C7; font-size: 12px;")
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.task_label)

        # 状态标签
        self.state_label = QLabel("空闲")
        state_font = QFont()
        state_font.setPointSize(10)
        self.state_label.setFont(state_font)
        self.state_label.setStyleSheet("color: #95A5A6;")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.state_label)

        # 倒计时显示
        self.time_label = QLabel("00:00")
        time_font = QFont()
        time_font.setPointSize(32)
        time_font.setBold(True)
        self.time_label.setFont(time_font)
        self.time_label.setStyleSheet("color: #ECF0F1;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #34495E;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #27AE60;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.start_btn = QPushButton("▶ 开始")
        self.start_btn.setFixedHeight(28)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ECC71;
            }
        """)
        self.start_btn.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setFixedHeight(28)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QPushButton:disabled {
                background-color: #7F8C8D;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        btn_layout.addWidget(self.stop_btn)

        self.skip_btn = QPushButton("⏭")
        self.skip_btn.setFixedSize(28, 28)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        self.skip_btn.clicked.connect(self._on_skip_clicked)
        btn_layout.addWidget(self.skip_btn)

        layout.addLayout(btn_layout)

    def _connect_signals(self):
        """连接服务信号"""
        self._service.state_changed.connect(self._on_state_changed)
        self._service.tick_signal.connect(self._on_tick)

    @pyqtSlot(str)
    def _on_state_changed(self, state):
        """状态变化处理"""
        self._update_ui()

    @pyqtSlot(int)
    def _on_tick(self, remaining):
        """每秒tick处理"""
        self._update_time_display(remaining)

    def _update_ui(self):
        """更新UI"""
        from services.pomodoro_service import PomodoroState

        state = self._service.state
        self.state_label.setText(self._service.get_state_display())

        # 任务名称
        task_type, task_id, task_title = self._service.current_task
        if task_title:
            self.task_label.setText(task_title)
        elif task_id:
            self.task_label.setText("任务进行中...")
        else:
            self.task_label.setText("未选择任务")

        # 根据状态更新按钮
        if state == PomodoroState.IDLE:
            self.start_btn.setEnabled(True)
            self.start_btn.setText("▶ 开始")
            self.stop_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
            self.progress_bar.setValue(0)
            self.time_label.setText("00:00")
        elif state == PomodoroState.WORKING:
            self.start_btn.setEnabled(True)
            self.start_btn.setText("⏸ 暂停")
            self.stop_btn.setEnabled(True)
            self.skip_btn.setEnabled(True)
            # 进度条颜色
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #34495E;
                    border: none;
                    border-radius: 3px;
                }
                QProgressBar::chunk {
                    background-color: #E74C3C;
                    border-radius: 3px;
                }
            """)
        elif state in (PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            self.start_btn.setEnabled(True)
            self.start_btn.setText("⏸ 暂停")
            self.stop_btn.setEnabled(True)
            self.skip_btn.setEnabled(True)
            # 进度条颜色 - 休息时绿色
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #34495E;
                    border: none;
                    border-radius: 3px;
                }
                QProgressBar::chunk {
                    background-color: #27AE60;
                    border-radius: 3px;
                }
            """)

        self._update_time_display(self._service.remaining_seconds)

    def _update_time_display(self, remaining):
        """更新时间显示"""
        self.time_label.setText(self._service.format_time(remaining))

        # 更新进度条
        from services.pomodoro_service import PomodoroState
        state = self._service.state
        if state == PomodoroState.IDLE:
            return

        total = 0
        if state == PomodoroState.WORKING:
            total = int(self._service._get_duration_work())
        elif state == PomodoroState.SHORT_BREAK:
            total = int(self._service._get_duration_short_break())
        elif state == PomodoroState.LONG_BREAK:
            total = int(self._service._get_duration_long_break())

        if total > 0:
            progress = int((1 - remaining / total) * 100)
            self.progress_bar.setValue(progress)

    def _on_start_clicked(self):
        """开始/暂停按钮点击"""
        from services.pomodoro_service import PomodoroState

        if self._service.state == PomodoroState.IDLE:
            self._service.start_work()
        elif self._service.state == PomodoroState.WORKING:
            self._service.pause()
            self.start_btn.setText("▶ 继续")
        elif self._service.state in (PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            self._service.pause()
            self.start_btn.setText("▶ 继续")

    def _on_stop_clicked(self):
        """停止按钮点击"""
        self._service.stop()

    def _on_skip_clicked(self):
        """跳过按钮点击"""
        self._service.skip()

    def _on_close(self):
        """关闭按钮点击"""
        self._service.stop()
        self.hide()

    def set_task(self, task_type, task_id, task_title):
        """设置当前任务"""
        self._service.start_work(task_type, task_id, task_title)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self._dragging = False
