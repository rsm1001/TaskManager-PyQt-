"""
Pomodoro Service - 番茄钟服务模块
核心计时逻辑，状态机管理
"""

import logging
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from config import pomodoro_config as config

logger = logging.getLogger(__name__)


class PomodoroState(Enum):
    """番茄钟状态"""
    IDLE = "idle"           # 空闲
    WORKING = "working"     # 工作中
    SHORT_BREAK = "short_break"   # 短休息
    LONG_BREAK = "long_break"     # 长休息


class PomodoroService(QObject):
    """番茄钟服务"""

    # 信号
    state_changed = pyqtSignal(str)           # 状态变化信号
    tick_signal = pyqtSignal(int)               # 每秒tick，参数为剩余秒数
    session_completed = pyqtSignal(int)         # 一个周期完成，参数为完成的工作次数
    task_started = pyqtSignal(str, str, str)   # 任务开始（task_type, task_id, task_title）
    task_stopped = pyqtSignal()                # 任务停止

    def __init__(self, data_manager):
        super().__init__()
        self._dm = data_manager
        self._state = PomodoroState.IDLE
        self._remaining_seconds = 0
        self._completed_work_sessions = 0  # 累计完成的工作次数
        self._current_task_type = None
        self._current_task_id = None
        self._current_task_title = ""
        self._timer = QTimer()
        self._timer.timeout.connect(self._on_timer_tick)
        logger.info("PomodoroService 初始化完成")

    @property
    def state(self):
        return self._state

    @property
    def remaining_seconds(self):
        return self._remaining_seconds

    @property
    def completed_sessions(self):
        return self._completed_work_sessions

    @property
    def current_task(self):
        return self._current_task_type, self._current_task_id, self._current_task_title

    def _get_duration(self, config_key, default):
        """从配置获取时长（秒）"""
        val = self._dm.get_config(config_key, str(default))
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def _get_duration_work(self):
        return self._get_duration(config.CONFIG_WORK_DURATION, config.DEFAULT_WORK_DURATION)

    def _get_duration_short_break(self):
        return self._get_duration(config.CONFIG_SHORT_BREAK, config.DEFAULT_SHORT_BREAK)

    def _get_duration_long_break(self):
        return self._get_duration(config.CONFIG_LONG_BREAK, config.DEFAULT_LONG_BREAK)

    def start_work(self, task_type=None, task_id=None, task_title=""):
        """开始工作周期"""
        if self._state == PomodoroState.WORKING:
            logger.warning("当前已在工作中，无法重复启动")
            return

        self._state = PomodoroState.WORKING
        self._remaining_seconds = self._get_duration_work()
        self._current_task_type = task_type
        self._current_task_id = task_id
        self._current_task_title = task_title

        self._timer.start(1000)  # 每秒触发
        logger.info(f"开始工作: {task_title or '无任务'} ({self._remaining_seconds}秒)")
        self.state_changed.emit(self._state.value)
        if task_type and task_id:
            self.task_started.emit(task_type, task_id, task_title)

    def start_short_break(self):
        """开始短休息"""
        if self._state == PomodoroState.WORKING:
            self._completed_work_sessions += 1
            self.session_completed.emit(self._completed_work_sessions)
            logger.info(f"工作周期完成，已完成 {self._completed_work_sessions} 个番茄钟")

        self._state = PomodoroState.SHORT_BREAK
        self._remaining_seconds = self._get_duration_short_break()
        self._timer.start(1000)
        logger.info(f"开始短休息 ({self._remaining_seconds}秒)")
        self.state_changed.emit(self._state.value)

    def start_long_break(self):
        """开始长休息"""
        self._state = PomodoroState.LONG_BREAK
        self._remaining_seconds = self._get_duration_long_break()
        self._timer.start(1000)
        logger.info(f"开始长休息 ({self._remaining_seconds}秒)")
        self.state_changed.emit(self._state.value)

    def stop(self):
        """停止计时"""
        self._timer.stop()
        was_running = self._state != PomodoroState.IDLE
        self._state = PomodoroState.IDLE
        self._remaining_seconds = 0
        self._current_task_type = None
        self._current_task_id = None
        self._current_task_title = ""
        logger.info("番茄钟已停止")
        self.state_changed.emit(self._state.value)
        if was_running:
            self.task_stopped.emit()

    def pause(self):
        """暂停计时"""
        if self._state != PomodoroState.IDLE:
            self._timer.stop()
            logger.info("番茄钟已暂停")

    def resume(self):
        """恢复计时"""
        if self._state != PomodoroState.IDLE and not self._timer.isActive():
            self._timer.start(1000)
            logger.info("番茄钟已恢复")

    def skip(self):
        """跳过当前阶段，进入下一个"""
        if self._state == PomodoroState.WORKING:
            self._completed_work_sessions += 1
            self.session_completed.emit(self._completed_work_sessions)
            self._decide_next_after_work()
        elif self._state == PomodoroState.SHORT_BREAK:
            self._decide_next_after_break()
        elif self._state == PomodoroState.LONG_BREAK:
            self._state = PomodoroState.IDLE
            self._remaining_seconds = 0
            self.state_changed.emit(self._state.value)

    def _on_timer_tick(self):
        """每秒触发"""
        self._remaining_seconds -= 1
        self.tick_signal.emit(self._remaining_seconds)

        if self._remaining_seconds <= 0:
            self._timer.stop()
            self._on_phase_completed()

    def _on_phase_completed(self):
        """阶段完成"""
        if self._state == PomodoroState.WORKING:
            self._completed_work_sessions += 1
            self.session_completed.emit(self._completed_work_sessions)
            logger.info(f"工作周期完成！已累计 {self._completed_work_sessions} 个番茄钟")

            auto_start = self._dm.get_config(config.CONFIG_AUTO_START_BREAK, '0') == '1'
            if auto_start:
                self._decide_next_after_work()
            else:
                self._state = PomodoroState.IDLE
                self.state_changed.emit(self._state.value)

        elif self._state == PomodoroState.SHORT_BREAK:
            logger.info("短休息结束")
            auto_start = self._dm.get_config(config.CONFIG_AUTO_START_WORK, '0') == '1'
            if auto_start:
                self.start_work(self._current_task_type, self._current_task_id, self._current_task_title)
            else:
                self._state = PomodoroState.IDLE
                self.state_changed.emit(self._state.value)

        elif self._state == PomodoroState.LONG_BREAK:
            logger.info("长休息结束")
            self._state = PomodoroState.IDLE
            self._remaining_seconds = 0
            self._completed_work_sessions = 0  # 重置计数
            self.state_changed.emit(self._state.value)

    def _decide_next_after_work(self):
        """工作阶段完成后决定下一个阶段"""
        if self._completed_work_sessions > 0 and self._completed_work_sessions % config.LONG_BREAK_INTERVAL == 0:
            self.start_long_break()
        else:
            self.start_short_break()

    def _decide_next_after_break(self):
        """休息阶段完成后决定下一个阶段"""
        self.start_work(self._current_task_type, self._current_task_id, self._current_task_title)

    def get_state_display(self):
        """获取状态的友好显示"""
        state_labels = {
            PomodoroState.IDLE: "空闲",
            PomodoroState.WORKING: "专注中",
            PomodoroState.SHORT_BREAK: "休息中",
            PomodoroState.LONG_BREAK: "长休息"
        }
        return state_labels.get(self._state, "未知")

    def format_time(self, seconds=None):
        """格式化时间为 MM:SS"""
        if seconds is None:
            seconds = self._remaining_seconds
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
