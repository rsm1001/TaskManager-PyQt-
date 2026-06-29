"""
时段编排器 - 时段 CRUD 与展示层辅助
通过依赖注入复用 TimePeriodManager
"""
import logging
from typing import Dict, List, Optional, Tuple, Callable

logger = logging.getLogger(__name__)


class TimePeriodOrchestrator:
    """时段编排器

    职责：
        - 时段 CRUD（委托 TimePeriodManager）
        - 删除时段时联动：把引用此 id 的三类任务的 time_period_id 置空
        - 渲染辅助：根据 id 反查展示文本，统一处理"未设时段/已删除"语义
    """

    # 渲染文本常量
    LABEL_NONE = "未设时段"
    LABEL_MISSING = "已删除"

    def __init__(
        self,
        time_period_manager,
        daily_task_manager,
        todo_task_manager,
        entertainment_task_manager,
    ) -> None:
        self._mgr = time_period_manager
        self._daily = daily_task_manager
        self._todo = todo_task_manager
        self._entertainment = entertainment_task_manager

    # ---------------- CRUD ----------------

    def get_all(self) -> List:
        return self._mgr.get_all()

    def get_by_id(self, period_id: Optional[str]):
        return self._mgr.get_by_id(period_id)

    def create(
        self,
        name: str,
        start_time: str = "",
        end_time: str = "",
        order_index: int = 0,
        color: str = "",
    ):
        return self._mgr.create(
            name=name,
            start_time=start_time,
            end_time=end_time,
            order_index=order_index,
            color=color,
        )

    def update(self, period_id: str, **kwargs) -> bool:
        return self._mgr.update(period_id, **kwargs)

    def delete(self, period_id: str) -> bool:
        """删除时段，并把引用此 id 的任务 time_period_id 置空（保留任务本身）"""
        period = self._mgr.get_by_id(period_id)
        if not period:
            return False
        # 联动：把所有引用此 period_id 的任务 time_period_id 置空
        self._clear_period_refs(period_id)
        return self._mgr.delete(period_id)

    def reorder(self, ordered_ids: List[str]) -> bool:
        return self._mgr.reorder(ordered_ids)

    def to_dict(self, period):
        return self._mgr.to_dict(period)

    # ---------------- 渲染辅助 ----------------

    def get_id_to_name_map(self) -> Dict[str, str]:
        return self._mgr.get_id_to_name_map()

    def resolve_period_label(self, period_id: Optional[str]) -> str:
        """根据 id 返回界面展示文本

        规则：
            - id 为空（None / 空字符串） → "未设时段"
            - id 存在但找不到对应时段 → "已删除"
            - id 命中 → 返回时段 name
        """
        if not period_id:
            return self.LABEL_NONE
        period = self._mgr.get_by_id(period_id)
        if period is None:
            return self.LABEL_MISSING
        return period.name

    def resolve_period_display(self, period_id: Optional[str]) -> str:
        """返回「名称 起止」复合显示串（任务表格里的时段列用）

        - id 为空 → "未设时段"
        - id 找不到 → "已删除"
        - id 命中且无起止 → 仅返回 name
        - id 命中且有起止 → 例如 "上午 07:00~12:00"
        """
        if not period_id:
            return self.LABEL_NONE
        period = self._mgr.get_by_id(period_id)
        if period is None:
            return self.LABEL_MISSING
        base = period.name
        if period.start_time or period.end_time:
            start = period.start_time or "--:--"
            end = period.end_time or "--:--"
            return f"{base} {start}~{end}"
        return base

    def get_filter_options(self) -> List[Tuple[str, Optional[str]]]:
        """生成时段筛选下拉框的 (显示文本, 对应 id 或 None) 列表

        None 表示"全部时段"；空字符串 "" 表示"未设时段"；其它 id 表示对应时段。
        """
        options: List[Tuple[str, Optional[str]]] = [("全部时段", None)]
        for period in self.get_all():
            options.append((period.name, period.id))
        # 把"未设时段"放在最后，便于用户单独筛 NULL
        options.append((self.LABEL_NONE, ""))
        return options

    # ---------------- 内部 ----------------

    def _clear_period_refs(self, period_id: str) -> None:
        """把三类任务里 time_period_id 等于 period_id 的都置 None（保留任务）"""
        try:
            self._daily.clear_time_period_refs(period_id)
        except Exception as exc:
            logger.warning("清理每日任务时段引用失败: %s", exc)
        try:
            self._todo.clear_time_period_refs(period_id)
        except Exception as exc:
            logger.warning("清理待办事项时段引用失败: %s", exc)
        try:
            self._entertainment.clear_time_period_refs(period_id)
        except Exception as exc:
            logger.warning("清理娱乐任务时段引用失败: %s", exc)
