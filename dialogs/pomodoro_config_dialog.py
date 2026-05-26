"""
Pomodoro Config Dialog - 番茄钟配置对话框
"""

import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QSpinBox, QCheckBox, QPushButton, QGroupBox,
                              QFormLayout)
from PyQt6.QtCore import Qt
from config import pomodoro_config as config

logger = logging.getLogger(__name__)


class PomodoroConfigDialog(QDialog):
    """番茄钟配置对话框"""

    def __init__(self, parent, data_manager):
        super().__init__(parent)
        self._dm = data_manager
        self.setWindowTitle("番茄钟设置")
        self.setModal(True)
        self.resize(400, 300)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 时长设置
        duration_group = QGroupBox("时间设置（分钟）")
        duration_layout = QFormLayout()

        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setSuffix(" 分钟")
        duration_layout.addRow("工作时长:", self.work_spin)

        self.short_break_spin = QSpinBox()
        self.short_break_spin.setRange(1, 60)
        self.short_break_spin.setSuffix(" 分钟")
        duration_layout.addRow("短休息:", self.short_break_spin)

        self.long_break_spin = QSpinBox()
        self.long_break_spin.setRange(1, 60)
        self.long_break_spin.setSuffix(" 分钟")
        duration_layout.addRow("长休息:", self.long_break_spin)

        self.long_break_interval_spin = QSpinBox()
        self.long_break_interval_spin.setRange(1, 10)
        duration_layout.addRow("长休息间隔:", self.long_break_interval_spin)

        duration_group.setLayout(duration_layout)
        layout.addWidget(duration_group)

        # 自动开始
        auto_group = QGroupBox("自动开始")
        auto_layout = QVBoxLayout()

        self.auto_start_break_check = QCheckBox("工作结束后自动开始休息")
        auto_layout.addWidget(self.auto_start_break_check)

        self.auto_start_work_check = QCheckBox("休息结束后自动开始工作")
        auto_layout.addWidget(self.auto_start_work_check)

        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)

        # 提示
        hint_label = QLabel("提示：番茄钟会记录您在每个任务上花费的时间，帮助您了解任务耗时。")
        hint_label.setStyleSheet("color: gray; font-size: 11px;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _load_settings(self):
        """加载当前设置"""
        work_sec = int(self._dm.get_config(config.CONFIG_WORK_DURATION, str(config.DEFAULT_WORK_DURATION)))
        short_sec = int(self._dm.get_config(config.CONFIG_SHORT_BREAK, str(config.DEFAULT_SHORT_BREAK)))
        long_sec = int(self._dm.get_config(config.CONFIG_LONG_BREAK, str(config.DEFAULT_LONG_BREAK)))

        self.work_spin.setValue(work_sec // 60)
        self.short_break_spin.setValue(short_sec // 60)
        self.long_break_spin.setValue(long_sec // 60)

        # 从config模块获取默认间隔
        from config import pomodoro_config
        interval_val = self._dm.get_config("pomodoro_long_break_interval", str(pomodoro_config.LONG_BREAK_INTERVAL))
        self.long_break_interval_spin.setValue(int(interval_val))

        self.auto_start_break_check.setChecked(
            self._dm.get_config(config.CONFIG_AUTO_START_BREAK, '0') == '1'
        )
        self.auto_start_work_check.setChecked(
            self._dm.get_config(config.CONFIG_AUTO_START_WORK, '0') == '1'
        )

    def _on_ok(self):
        """保存设置"""
        work_sec = self.work_spin.value() * 60
        short_sec = self.short_break_spin.value() * 60
        long_sec = self.long_break_spin.value() * 60
        interval = self.long_break_interval_spin.value()

        self._dm.set_config(config.CONFIG_WORK_DURATION, str(work_sec))
        self._dm.set_config(config.CONFIG_SHORT_BREAK, str(short_sec))
        self._dm.set_config(config.CONFIG_LONG_BREAK, str(long_sec))
        self._dm.set_config("pomodoro_long_break_interval", str(interval))
        self._dm.set_config(config.CONFIG_AUTO_START_BREAK, '1' if self.auto_start_break_check.isChecked() else '0')
        self._dm.set_config(config.CONFIG_AUTO_START_WORK, '1' if self.auto_start_work_check.isChecked() else '0')

        logger.info("番茄钟设置已保存")
        self.accept()
