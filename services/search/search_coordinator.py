"""
搜索协调器
封装搜索结果导航和任务选择逻辑，与 UI 解耦
"""

import logging
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SearchCoordinator:
    """搜索协调器 - 处理搜索结果的双击导航和任务选择"""

    def __init__(self, window):
        """
        Args:
            window: TaskManagerMainWindow 实例
        """
        self._window = window
        # 任务类型到 Tab 页索引的映射
        self._tab_index_map = {
            'daily': 1,
            'todo': 2,
            'entertainment': 3,
            'shortcuts': 4,
        }
        # 任务类型到表格和刷新函数的映射
        self._table_map = {
            'daily': (None, None),  # 会在运行时通过 window 获取
            'todo': (None, None),
            'entertainment': (None, None),
            'shortcuts': (None, None),
        }
        logger.info("SearchCoordinator 初始化完成")

    def navigate_to_task(self, row: int) -> bool:
        """
        双击搜索结果行，跳转到对应任务的Tab并选中

        Args:
            row: 搜索结果表格的行索引

        Returns:
            bool: 是否成功跳转
        """
        type_item = self._window.search_results_table.item(row, 0)
        if type_item is None:
            logger.debug(f"搜索结果行 {row} 的类型列为空")
            return False

        task_type_map = {
            '每日任务': 'daily',
            '待办事项': 'todo',
            '娱乐任务': 'entertainment',
            '快捷入口': 'shortcuts',
        }

        type_text = type_item.text()
        target_tab = task_type_map.get(type_text)
        if target_tab is None:
            logger.warning(f"未知的任务类型: {type_text}")
            return False

        # 获取任务ID
        task_id = type_item.data(self._get_user_role())
        if not task_id:
            logger.warning(f"搜索结果行 {row} 缺少任务ID")
            return False

        # 切换到对应 Tab
        target_index = self._tab_index_map.get(target_tab)
        if target_index is not None:
            self._window.tab_widget.setCurrentIndex(target_index)

        # 选中对应行
        return self._select_task_in_table(target_tab, task_id)

    def _get_user_role(self):
        """获取 Qt UserRole（兼容 PyQt6）"""
        from PyQt6.QtCore import Qt
        return Qt.ItemDataRole.UserRole

    def _select_task_in_table(self, task_type: str, task_id: str) -> bool:
        """
        在指定类型的表格中选中指定ID的任务

        Args:
            task_type: 任务类型 ('daily', 'todo', 'entertainment', 'shortcuts')
            task_id: 任务ID

        Returns:
            bool: 是否成功选中
        """
        table = getattr(self._window, f'{task_type}_table', None)
        if table is None:
            logger.error(f"找不到任务类型 {task_type} 对应的表格")
            return False

        # 重新加载表格确保数据最新
        reload_func = getattr(self._window, f'load_{task_type}_tasks', None)
        if reload_func:
            reload_func()

        # 查找并选中对应行
        for row in range(table.rowCount()):
            if task_type == 'shortcuts':
                # 快捷入口的 task_id 存储在按钮属性中
                btn = table.cellWidget(row, 0)
                if btn and btn.property('task_id') == task_id:
                    table.selectRow(row)
                    logger.info(f"已选中快捷入口: {task_id}")
                    return True
            else:
                # 普通任务的 task_id 存储在 UserRole 中
                item = table.item(row, 0)
                if item and item.data(self._get_user_role()) == task_id:
                    table.selectRow(row)
                    table.scrollToItem(item)
                    logger.info(f"已选中任务: {task_type} - {task_id}")
                    return True

        logger.warning(f"在 {task_type} 中找不到任务ID: {task_id}")
        return False

    def clear_search_results(self):
        """清除搜索结果"""
        self._window.search_results_table.setRowCount(0)
        self._window.search_status_label.setText('请输入关键词搜索')
        logger.debug("搜索结果已清除")

    def update_status_label(self, text: str):
        """更新搜索状态标签"""
        self._window.search_status_label.setText(text)
