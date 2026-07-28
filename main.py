"""任务管理器主窗口入口与界面组装。"""

import os
import sys

# LobsterAI 的嵌入式 Python 运行时不会自动将脚本目录加入 sys.path。
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QFileIconProvider, QMainWindow, QStatusBar, QTabWidget, QVBoxLayout, QWidget

import config.config
from components.main_window.ui_components import (
    create_daily_tab_ui,
    create_entertainment_tab_ui,
    create_search_tab_ui,
    create_shortcuts_tab_ui,
    create_todo_tab_ui,
)
from components.main_window.ui_elements import create_menu_bar, create_toolbar
from managers.application.data_manager import DataManager
from services.search.search_coordinator import SearchCoordinator
from services.application.window_task_operations import TaskOperationHandler
from ui.main_window.table_actions import MainWindowTableActionsMixin
from ui.main_window.task_actions import MainWindowTaskActionsMixin
from ui.main_window.tools import MainWindowToolsMixin
from utils.logging_config import setup_logging

setup_logging(log_level=config.config.LOG_LEVEL)


class TaskManagerMainWindow(
    MainWindowTableActionsMixin,
    MainWindowTaskActionsMixin,
    MainWindowToolsMixin,
    QMainWindow,
):
    """只负责组合依赖和界面，业务行为由职责模块提供。"""

    def __init__(self):
        super().__init__()
        config.config.ensure_directories()
        self.data_manager = DataManager()
        self._task_handler = TaskOperationHandler(self)
        self.daily_tag_filter_value = ''
        self.todo_tag_filter_value = ''
        self.entertainment_tag_filter_value = ''
        self._status_switching_row = -1
        self._status_switch_timestamps = {}
        self._pomodoro_service = self.data_manager._get_pomodoro_service()
        self._pomodoro_toolbar = None
        self._pomodoro_toolbar_positioned = False
        self._itinerary_widget = None
        self._itinerary_positioned = False
        self.filter_arranged_tasks = False
        self._arranged_task_refs = set()
        self._search_coordinator = SearchCoordinator(self)
        self.init_ui()
        self._init_global_shortcuts()
        self.load_data()

    def _init_global_shortcuts(self):
        """Register the application-wide itinerary show/hide shortcut."""
        self._itinerary_shortcut = QShortcut(QKeySequence('Alt+Q'), self)
        self._itinerary_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._itinerary_shortcut.activated.connect(self.show_itinerary)

    def init_ui(self):
        self.setWindowTitle(config.config.WINDOW_TITLE)
        self.setGeometry(100, 100, config.config.WINDOW_WIDTH, config.config.WINDOW_HEIGHT)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        self.create_search_tab()
        self.create_daily_tab()
        self.create_todo_tab()
        self.create_entertainment_tab()
        self.create_shortcuts_tab()
        self.create_menu_bar()
        self.create_toolbar()
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('就绪')

    def create_menu_bar(self):
        create_menu_bar(self)

    def create_toolbar(self):
        create_toolbar(self)

    def create_daily_tab(self):
        self.tab_widget.addTab(create_daily_tab_ui(self), '每日必做')

    def create_todo_tab(self):
        self.tab_widget.addTab(create_todo_tab_ui(self), '待办事项')

    def create_entertainment_tab(self):
        self.tab_widget.addTab(create_entertainment_tab_ui(self), '娱乐任务')

    def create_shortcuts_tab(self):
        self.tab_widget.addTab(create_shortcuts_tab_ui(self), '快捷入口')

    def create_search_tab(self):
        self.tab_widget.insertTab(0, create_search_tab_ui(self), '搜索')


def main():
    app = QApplication(sys.argv)
    runtime_icon = QFileIconProvider().icon(QFileInfo(sys.executable))
    if not runtime_icon.isNull():
        app.setWindowIcon(runtime_icon)
    window = TaskManagerMainWindow()
    window.setWindowIcon(app.windowIcon())
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
