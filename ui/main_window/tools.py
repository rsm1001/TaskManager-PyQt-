"""主窗口的导入导出、浮窗和系统工具行为。"""

import logging

from PyQt6.QtWidgets import QFileDialog, QDialog, QMessageBox

import config.config
from components.itinerary_widget import ItineraryWidget
from components.pomodoro_toolbar import PomodoroToolbarWidget
from dialogs.json_examples_dialog import JsonExamplesDialog
from dialogs.pomodoro_config_dialog import PomodoroConfigDialog
from dialogs.trash_dialog import TrashDialog
from utils.ui_messages import (
    confirm_data_import,
    show_about_dialog,
    show_export_failure,
    show_export_success,
    show_import_failure,
    show_import_success,
    show_statistics_dialog,
)

logger = logging.getLogger(__name__)


class MainWindowToolsMixin:
    """管理主窗口的辅助工具和行程状态。"""

    def export_data(self):
        filepath, _ = QFileDialog.getSaveFileName(self, '导出数据', 'tasks_export.json', 'JSON Files (*.json)')
        if not filepath:
            return
        if self.data_manager.export_to_json(filepath):
            show_export_success()
        else:
            show_export_failure()

    def import_data(self):
        filepath, _ = QFileDialog.getOpenFileName(self, '导入数据', '', 'JSON Files (*.json)')
        if not filepath or confirm_data_import(self) != QMessageBox.StandardButton.Yes:
            return
        if self.data_manager.import_from_json(filepath):
            self.load_data()
            show_import_success(self)
            self.status_bar.showMessage('数据导入成功')
        else:
            show_import_failure(self)
            self.status_bar.showMessage('数据导入失败')

    def show_statistics(self):
        show_statistics_dialog(self.data_manager.get_statistics())

    def run_type_check(self):
        from utils.ui_messages import show_type_check_dialog
        show_type_check_dialog(self)

    def _refresh_arranged_cache(self):
        weekday = self.daily_weekday_combo.currentText()
        day_of_week = config.config.WEEKDAY_NAMES.index(weekday) + 1 if weekday in config.config.WEEKDAY_NAMES else None
        self._arranged_task_refs = self.data_manager.get_itinerary_task_refs(day_of_week=day_of_week)

    def _get_arranged_task_refs(self):
        return self._arranged_task_refs

    def show_itinerary(self):
        from PyQt6 import sip
        if self._itinerary_widget is not None and sip.isdeleted(self._itinerary_widget):
            self._itinerary_widget, self._itinerary_positioned = None, False

        created = self._itinerary_widget is None
        if created:
            self._itinerary_widget = ItineraryWidget(self.data_manager, self)
            self._itinerary_widget.destroyed.connect(lambda: self._clear_itinerary_reference())
            self._refresh_arranged_cache()
        # A minimized top-level itinerary remains "visible" to Qt. Restore it
        # instead of treating Alt+Q as a request to hide the window again.
        if self._itinerary_widget.isMinimized():
            self._itinerary_widget.refresh_itinerary_data()
            self._itinerary_widget.showNormal()
            self._itinerary_widget.raise_()
            self._itinerary_widget.activateWindow()
            self._refresh_arranged_cache()
            return

        if self._itinerary_widget.isVisible():
            self._itinerary_widget.hide()
            return

        if not created:
            self._itinerary_widget.refresh_itinerary_data()
        if not self._itinerary_positioned and not self._itinerary_widget.has_saved_position():
            geometry = self.geometry()
            self._itinerary_widget.move(geometry.center().x() - self._itinerary_widget.width() // 2, geometry.center().y() - self._itinerary_widget.height() // 2)
        self._itinerary_positioned = True
        self._itinerary_widget.showNormal()
        self._itinerary_widget.raise_()
        self._itinerary_widget.activateWindow()
        self._refresh_arranged_cache()

    def _clear_itinerary_reference(self):
        self._itinerary_widget, self._itinerary_positioned = None, False

    def refresh_arranged_cache(self):
        self._refresh_arranged_cache()

    def refresh_itinerary_after_task_update(self):
        """Refresh the live itinerary after a bound shortcut is edited."""
        from PyQt6 import sip

        self._refresh_arranged_cache()
        itinerary_widget = getattr(self, '_itinerary_widget', None)
        if itinerary_widget is not None and not sip.isdeleted(itinerary_widget):
            itinerary_widget.refresh_itinerary_data()

    def refresh_itinerary_after_task_deletion(self):
        """Refresh the live itinerary after source tasks and references are deleted."""
        from PyQt6 import sip

        self._refresh_arranged_cache()
        itinerary_widget = getattr(self, '_itinerary_widget', None)
        if itinerary_widget is not None and not sip.isdeleted(itinerary_widget):
            itinerary_widget.refresh_itinerary_data()

    def toggle_arranged_tasks_filter(self, checked):
        self.filter_arranged_tasks = checked
        if checked:
            self._refresh_arranged_cache()
        self.load_daily_tasks()
        self.load_todo_tasks()
        self.load_entertainment_tasks()

    def show_pomodoro(self):
        from PyQt6 import sip
        if self._pomodoro_toolbar is not None and sip.isdeleted(self._pomodoro_toolbar):
            self._pomodoro_toolbar, self._pomodoro_toolbar_positioned = None, False
        if self._pomodoro_toolbar is None:
            self._pomodoro_toolbar = PomodoroToolbarWidget(self._pomodoro_service, self)
            self._pomodoro_toolbar.destroyed.connect(lambda: self._clear_pomodoro_reference())
        if self._pomodoro_toolbar.isVisible():
            self._pomodoro_toolbar.hide()
            return
        if not self._pomodoro_toolbar_positioned:
            geometry = self.geometry()
            self._pomodoro_toolbar.move(geometry.right() - self._pomodoro_toolbar.width() - 10, geometry.bottom() - self._pomodoro_toolbar.height() - 10)
            self._pomodoro_toolbar_positioned = True
        self._pomodoro_toolbar.show()

    def _clear_pomodoro_reference(self):
        self._pomodoro_toolbar, self._pomodoro_toolbar_positioned = None, False

    def show_schulte_grid(self):
        from PyQt6 import sip
        if hasattr(self, 'schulte_grid') and not sip.isdeleted(self.schulte_grid):
            if self.schulte_grid.isVisible():
                self.schulte_grid.hide()
            else:
                self._move_to_center(self.schulte_grid)
                self.schulte_grid.show()
            return
        from components.schulte_grid import SchulteGridWidget
        self.schulte_grid = SchulteGridWidget()
        self._move_to_center(self.schulte_grid)
        self.schulte_grid.show()

    def _move_to_center(self, widget):
        geometry = self.geometry()
        widget.move(geometry.center().x() - widget.width() // 2, geometry.center().y() - widget.height() // 2)

    def show_pomodoro_config(self):
        PomodoroConfigDialog(self, self.data_manager).exec()

    def show_time_period_settings(self):
        from components.main_window.ui_components import refresh_all_time_period_combos
        from dialogs.time_period_dialog import TimePeriodDialog
        dialog = TimePeriodDialog(self, self.data_manager)
        dialog.updated.connect(lambda: refresh_all_time_period_combos(self))
        dialog.exec()

    def show_json_examples(self):
        JsonExamplesDialog(self).exec()

    def show_about(self):
        show_about_dialog(self)

    def update_status_bar(self):
        try:
            stats = self.data_manager.get_statistics()
            duration = stats['daily'].get('pending_duration', 0)
            duration_text = f'{duration // 60}小时{duration % 60}分钟' if duration >= 60 else (f'{duration}分钟' if duration else '')
            pending = f'({duration_text})' if stats['daily'].get('pending', 0) else ''
            message = (f"每日: {stats['daily']['completed']}/{stats['daily']['total']} 完成 {pending} "
                       f"({stats['daily']['paused']} 暂弃不统计 | 待办: {stats['todo']['completed']}/{stats['todo']['total']} 完成 "
                       f"({stats['todo']['expired']} 过期, {stats['todo']['paused']} 暂弃不统计 | 娱乐: "
                       f"{stats['entertainment']['completed']}/{stats['entertainment']['total']} 完成 "
                       f"({stats['entertainment']['paused']} 暂弃不统计")
            self.status_bar.showMessage(message, 0)
        except Exception:
            logger.exception('更新状态栏失败', extra={'trace_id': 'status-bar'})
            self.status_bar.showMessage('获取统计数据时出错', 0)

    def update_task_row_style(self, table, row, is_completed):
        from utils.ui_messages import update_task_row_style
        update_task_row_style(table, row, is_completed)

    def closeEvent(self, event):
        # The itinerary is a separate top-level window. Hide it before accepting
        # the main-window close so it cannot keep the application alive invisibly.
        from PyQt6 import sip

        itinerary = getattr(self, '_itinerary_widget', None)
        if itinerary is not None and not sip.isdeleted(itinerary):
            itinerary.hide()
        self.data_manager.close_session()
        event.accept()

    def open_trash_dialog(self):
        if TrashDialog(self, self.data_manager).exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def is_auto_cleanup_enabled(self):
        return self.data_manager.get_config('auto_cleanup_unused_tags', '0') == '1'

    def cleanup_unused_tags_manual(self):
        result = self.data_manager._service_factory.get_tag_cleanup_service().cleanup_unused_tags()
        total_cleaned = sum(result.values())
        for name in ('daily_tag_filter', 'todo_tag_filter', 'entertainment_tag_filter', 'shortcut_tag_filter'):
            getattr(self, name).refresh_tags()
        QMessageBox.information(self, '清理完成', f"共清理了 {total_cleaned} 个未使用标签\n每日任务: {result.get('daily', 0)} 个\n待办事项: {result.get('todo', 0)} 个\n娱乐任务: {result.get('entertainment', 0)} 个\n快捷入口: {result.get('shortcut', 0)} 个")
        self.status_bar.showMessage(f'标签清理完成，共删除 {total_cleaned} 个')
