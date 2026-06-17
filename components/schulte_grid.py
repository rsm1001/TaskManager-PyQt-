"""
Schulte Grid Widget - 舒尔特方格训练浮动工具栏
随机颜色数字网格，按顺序点击 1-25
"""

import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QComboBox, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QPoint
from PyQt6.QtGui import QFont, QColor


class SchulteGridWidget(QWidget):
    """舒尔特方格训练浮动工具栏"""

    GRID_SIZE = 5
    TOTAL_CELLS = GRID_SIZE * GRID_SIZE  # 25

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cells = []          # 格子按钮列表
        self._expected = 1         # 下一个应该点击的数字
        self._error_count = 0     # 错误次数
        self._started = False     # 是否已开始
        self._elapsed_ms = 0      # 已用时间（毫秒）
        self._timer = QTimer()    # 计时器
        self._timer.timeout.connect(self._on_timer_tick)
        self._current_cell = None  # 当前高亮的格子
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("舒尔特方格训练")
        self.setFixedWidth(420)
        self.setFixedHeight(520)
        self.setWindowFlags(Qt.WindowType.Tool |
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._dragging = False
        self._drag_position = QPoint()
        self.setStyleSheet("""
            SchulteGridWidget {
                background-color: #2C3E50;
                border-radius: 10px;
                border: 1px solid #34495E;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 标题栏（可拖动）
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("🎯 舒尔特方格"))
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

        # 状态显示
        self.state_label = QLabel("点击「开始」启动训练")
        self.state_label.setFont(QFont("Microsoft YaHei", 10))
        self.state_label.setStyleSheet("color: #BDC3C7;")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.state_label)

        # 网格区域
        self._grid_layout = QGridLayout()
        self._grid_layout.setSpacing(6)
        self._create_grid()
        layout.addLayout(self._grid_layout)

        # 统计信息
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        self.time_label = QLabel("用时: 0.0s")
        self.time_label.setFont(QFont("Microsoft YaHei", 10))
        self.time_label.setStyleSheet("color: #ECF0F1;")
        stats_layout.addWidget(self.time_label)

        self.error_label = QLabel("错误: 0")
        self.error_label.setFont(QFont("Microsoft YaHei", 10))
        self.error_label.setStyleSheet("color: #E74C3C;")
        stats_layout.addWidget(self.error_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.start_btn = QPushButton("开始")
        self.start_btn.setFixedHeight(32)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ECC71;
            }
        """)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setFixedHeight(32)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495E;
                color: #ECF0F1;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4A6278;
            }
        """)
        self.reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.reset_btn)

        layout.addLayout(btn_layout)

    def _create_grid(self):
        """创建网格"""
        # 清除旧格子
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cells.clear()

        # 生成打乱顺序的数字 1-25
        numbers = list(range(1, self.TOTAL_CELLS + 1))
        random.shuffle(numbers)

        # 为每个数字生成随机颜色
        colors = self._generate_random_colors(self.TOTAL_CELLS)

        for i, num in enumerate(numbers):
            row = i // self.GRID_SIZE
            col = i % self.GRID_SIZE

            btn = QPushButton(str(num))
            btn.setFixedSize(68, 68)
            btn.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
            color = colors[i]
            btn.setStyleSheet(self._cell_style(color, False))
            btn.clicked.connect(lambda checked, n=num: self._on_cell_clicked(n))
            btn._num = num          # 保存数字
            btn._color = color      # 保存颜色
            self._grid_layout.addWidget(btn, row, col)
            self._cells.append(btn)

    def _generate_random_colors(self, count):
        """生成 count 种随机颜色"""
        colors = []
        for _ in range(count):
            # 使用 HSL 颜色空间，色相随机，饱和度和亮度适中
            h = random.randint(0, 359)   # 色相范围 0-359
            s = random.randint(160, 240)  # 高饱和度 0-255
            l = random.randint(100, 140)  # 适中亮度 0-255
            colors.append(QColor.fromHsl(h, s, l))
        return colors

    def _cell_style(self, color, is_active):
        """生成格子样式"""
        rgb = f"{color.red()}, {color.green()}, {color.blue()}"
        border_color = f"{min(color.red() + 40, 255)}, {min(color.green() + 40, 255)}, {min(color.blue() + 40, 255)}"
        if is_active:
            # 当前应该点击的格子 - 白色边框高亮
            return f"""
                QPushButton {{
                    background-color: rgb({rgb});
                    border: 3px solid #FFFFFF;
                    border-radius: 8px;
                    color: #FFFFFF;
                }}
                QPushButton:hover {{
                    background-color: rgb({min(color.red() + 30, 255)}, {min(color.green() + 30, 255)}, {min(color.blue() + 30, 255)});
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: rgb({rgb});
                    border: 2px solid rgb({border_color});
                    border-radius: 8px;
                    color: #FFFFFF;
                }}
                QPushButton:hover {{
                    background-color: rgb({min(color.red() + 20, 255)}, {min(color.green() + 20, 255)}, {min(color.blue() + 20, 255)});
                }}
            """

    def _on_cell_clicked(self, num):
        """格子点击处理"""
        if not self._started:
            # 未开始时点击无效
            return

        if num == self._expected:
            # 正确点击 - 不做任何改变，纯记忆训练
            self._expected += 1

            # 检查是否全部完成
            if self._expected > self.TOTAL_CELLS:
                self._finish()
        else:
            # 错误点击
            self._error_count += 1
            self.error_label.setText(f"错误: {self._error_count}")
            self._shake_cell(num)

    def _shake_cell(self, num):
        """错误点击时抖动格子"""
        for cell in self._cells:
            if cell._num == num:
                cell.setStyleSheet(self._error_style(cell._color))
                QTimer.singleShot(200, lambda: cell.setStyleSheet(self._cell_style(cell._color, False)))
                break

    def _error_style(self, color):
        """错误点击时的红色样式"""
        return f"""
            QPushButton {{
                background-color: #E74C3C;
                border: 3px solid #C0392B;
                border-radius: 8px;
                color: #FFFFFF;
            }}
        """

    def _on_start(self):
        """开始训练"""
        self._started = True
        self._expected = 1
        self._error_count = 0
        self._elapsed_ms = 0
        self.error_label.setText("错误: 0")
        self.state_label.setText("训练中... 请按顺序点击 1-25")
        self.start_btn.setEnabled(False)
        self._timer.start(100)  # 每100ms更新一次

    def _on_reset(self):
        """重置训练"""
        self._timer.stop()
        self._started = False
        self._expected = 1
        self._error_count = 0
        self._elapsed_ms = 0
        self.error_label.setText("错误: 0")
        self.time_label.setText("用时: 0.0s")
        self.state_label.setText("点击「开始」启动训练")
        self.start_btn.setEnabled(True)
        # 重新生成网格
        self._create_grid()

    def _on_timer_tick(self):
        """计时器更新"""
        self._elapsed_ms += 100
        seconds = self._elapsed_ms / 1000
        self.time_label.setText(f"用时: {seconds:.1f}s")

    def _finish(self):
        """完成训练"""
        self._timer.stop()
        self._started = False
        seconds = self._elapsed_ms / 1000
        self.state_label.setText(f"🎉 完成！用时 {seconds:.1f}秒，错误 {self._error_count} 次")
        self.start_btn.setEnabled(True)

    def _on_close(self):
        """关闭"""
        self._timer.stop()
        self.hide()

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
