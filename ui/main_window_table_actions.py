"""主窗口的数据加载和搜索行为。"""

from services.application.table_operations import (
    load_daily_tasks_to_table,
    load_entertainment_tasks_to_table,
    load_search_results_to_table,
    load_shortcut_history_to_table,
    load_shortcuts_to_table,
    load_todo_tasks_to_table,
    sort_todo_table_by_column,
    toggle_daily_task_status,
    toggle_entertainment_task_status,
    toggle_todo_task_status,
)


class MainWindowTableActionsMixin:
    """集中主窗口与表格服务的适配逻辑。"""

    def load_data(self):
        self.load_daily_tasks()
        self.load_todo_tasks()
        self.load_entertainment_tasks()
        self.load_shortcuts()
        self.load_shortcuts_history()
        self._load_claude_skip_permission_state()
        self._load_codex_skip_permission_state()
        self.update_status_bar()

    def load_daily_tasks(self):
        load_daily_tasks_to_table(self)

    def load_tasks_for_selected_weekday(self):
        if self.filter_arranged_tasks:
            self._refresh_arranged_cache()
            self.load_todo_tasks()
            self.load_entertainment_tasks()
        self.load_daily_tasks()

    def toggle_daily_task_status(self, row, column):
        toggle_daily_task_status(self, row, column)

    def load_todo_tasks(self):
        load_todo_tasks_to_table(self)

    def toggle_todo_task_status(self, row, column):
        toggle_todo_task_status(self, row, column)

    def sort_todo_table_by_column(self, column):
        sort_todo_table_by_column(self, column)

    def load_entertainment_tasks(self):
        load_entertainment_tasks_to_table(self)

    def toggle_entertainment_task_status(self, row, column):
        toggle_entertainment_task_status(self, row, column)

    def load_shortcuts(self):
        load_shortcuts_to_table(self)

    def load_shortcuts_history(self):
        load_shortcut_history_to_table(self)

    def on_search_text_changed(self, text):
        if not text.strip():
            self._search_coordinator.clear_search_results()
            return
        load_search_results_to_table(self)

    def on_search_clear(self):
        self.search_input.clear()
        self._search_coordinator.clear_search_results()

    def on_search_result_double_click(self, row, _column):
        self._search_coordinator.navigate_to_task(row)
