"""
快捷入口操作服务
封装快捷入口的打开、历史记录更新等业务逻辑
与 UI 解耦，通过事件或回调通知结果
"""

import logging
import os
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)


class ShortcutOperationService:
    """快捷入口操作服务 - 处理快捷入口业务逻辑"""

    def __init__(self, data_manager):
        """
        Args:
            data_manager: DataManager 实例
        """
        self._data_manager = data_manager
        logger.info("ShortcutOperationService 初始化完成")

    def open_shortcut(self, shortcut_id: str) -> Dict[str, Any]:
        """
        打开快捷入口并更新历史记录

        Args:
            shortcut_id: 快捷入口ID

        Returns:
            Dict containing 'success', 'message', and optionally 'data'
        """
        # 获取快捷入口数据
        shortcuts = self._data_manager.get_all_shortcuts()
        shortcut_data = next((s for s in shortcuts if s['id'] == shortcut_id), None)

        if not shortcut_data:
            logger.warning(f"快捷入口不存在: {shortcut_id}")
            return {'success': False, 'message': '快捷入口不存在'}

        # 打开快捷路径
        try:
            self._open_shortcut_path(
                shortcut_data['shortcut_path'],
                shortcut_data.get('action_type', 'open')
            )
        except Exception as e:
            logger.error(f"打开快捷路径失败: {e}", exc_info=True)
            return {'success': False, 'message': f'打开失败: {str(e)}'}

        # 添加到历史记录
        try:
            self._data_manager.add_or_update_history(
                shortcut_id,
                shortcut_data['title'],
                shortcut_data['shortcut_path'],
                shortcut_data.get('action_type', 'open')
            )
            logger.info(f"快捷入口已打开并更新历史: {shortcut_data['title']}")
        except Exception as e:
            logger.error(f"更新历史记录失败: {e}", exc_info=True)
            # 历史记录失败不影响主流程

        return {
            'success': True,
            'message': '打开成功',
            'data': {
                'shortcut_id': shortcut_id,
                'title': shortcut_data['title'],
                'path': shortcut_data['shortcut_path']
            }
        }

    def _open_shortcut_path(self, path: str, action_type: str = 'open'):
        """
        打开快捷路径或执行脚本

        Args:
            path: 快捷路径
            action_type: 操作类型 ('open' 或 'script')
        """
        import subprocess
        import sys

        if not path:
            raise ValueError("快捷路径不能为空")

        if action_type == 'script' or path.endswith('.bat') or path.endswith('.cmd'):
            # 执行脚本
            logger.info(f"执行脚本: {path}")
            if sys.platform == 'win32':
                subprocess.Popen(['cmd', '/c', 'start', '', path],
                               shell=True, cwd=os.path.dirname(path) or None)
            else:
                subprocess.Popen(['bash', path], cwd=os.path.dirname(path) or None)
        else:
            # 打开文件/文件夹
            logger.info(f"打开路径: {path}")
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])

    def get_history_limit(self) -> int:
        """获取历史记录缓存数量限制"""
        return self._data_manager.get_history_limit()

    def set_history_limit(self, limit: int) -> bool:
        """设置历史记录缓存数量限制"""
        result = self._data_manager.set_history_limit(limit)
        if result:
            logger.info(f"历史记录缓存限制已设置为: {limit}")
        return result

    def get_dangerously_skip_permissions(self) -> bool:
        """获取 Claude 启动时是否放权（--dangerously-skip-permissions）"""
        return self._data_manager.get_dangerously_skip_permissions()

    def set_dangerously_skip_permissions(self, enabled: bool) -> bool:
        """设置 Claude 启动时是否放权"""
        result = self._data_manager.set_dangerously_skip_permissions(enabled)
        if result:
            logger.info(f"Claude 启动放权设置已更新为: {enabled}")
        return result

    def get_codex_dangerously_skip_permissions(self) -> bool:
        """获取 Codex 启动时是否放权"""
        return self._data_manager.get_codex_dangerously_skip_permissions()

    def set_codex_dangerously_skip_permissions(self, enabled: bool) -> bool:
        """设置 Codex 启动时是否放权"""
        result = self._data_manager.set_codex_dangerously_skip_permissions(enabled)
        if result:
            logger.info(f"Codex 启动放权设置已更新为: {enabled}")
        return result

    def clear_history(self) -> int:
        """清空所有非置顶历史记录，返回删除数量"""
        count = self._data_manager.clear_all_unpinned_history()
        logger.info(f"已清空 {count} 条非置顶历史记录")
        return count
