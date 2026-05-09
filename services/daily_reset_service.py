"""
每日重置服务 - 封装每日任务状态重置逻辑
"""

from datetime import datetime, date
from models.model import DailyTask
import config.config


class DailyResetService:
    """每日重置服务，负责检查并执行每日任务状态重置"""

    def __init__(self, session, config_manager):
        """
        Args:
            session: 数据库会话
            config_manager: ConfigManager 实例
        """
        self.session = session
        self._config = config_manager

    def check_and_reset(self):
        """检查并执行每日重置"""
        last_reset = self._config.get("last_reset_date", "")
        try:
            last_reset_date = datetime.strptime(last_reset, "%Y-%m-%d").date() if last_reset else date.today()
            today = date.today()
            if last_reset_date < today:
                self._do_reset()
                self._config.set("last_reset_date", today.strftime("%Y-%m-%d"))
        except ValueError:
            self._do_reset()
            self._config.set("last_reset_date", date.today().strftime("%Y-%m-%d"))

    def _do_reset(self):
        """执行实际的重置操作"""
        today_weekday = datetime.now().weekday()
        weekday_names = config.config.WEEKDAY_NAMES
        today_name = weekday_names[today_weekday] if 0 <= today_weekday <= 6 else ''

        all_tasks = self.session.query(DailyTask).all()
        for task in all_tasks:
            if not task.week_day or task.week_day == today_name:
                if task.status == 'completed':
                    task.status = 'pending'
                    task.completed = False
        self.session.commit()
