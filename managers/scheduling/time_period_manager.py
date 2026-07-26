"""
时段管理器 - 封装 TimePeriod 模型的所有数据库操作
遵循 Repository 模式
"""
import logging
from typing import List, Optional, Dict

from models.model import TimePeriod

logger = logging.getLogger(__name__)


class TimePeriodManager:
    """时段管理器，负责 TimePeriod 表的 CRUD 与 id->name 字典查询"""

    def __init__(self, session):
        self.session = session

    def get_all(self) -> List[TimePeriod]:
        """获取所有时段，按 order_index 与 name 排序"""
        return self.session.query(TimePeriod).order_by(
            TimePeriod.order_index.asc(),
            TimePeriod.name.asc(),
        ).all()

    def get_by_id(self, period_id: Optional[str]) -> Optional[TimePeriod]:
        """按 id 查找时段，未命中返回 None"""
        if not period_id:
            return None
        return self.session.query(TimePeriod).filter(TimePeriod.id == period_id).first()

    def get_id_to_name_map(self) -> Dict[str, str]:
        """返回 {period_id: name} 字典，供渲染层批量反查名"""
        rows = self.session.query(TimePeriod.id, TimePeriod.name).all()
        return {row[0]: row[1] for row in rows if row[0]}

    def create(
        self,
        name: str,
        start_time: str = "",
        end_time: str = "",
        order_index: int = 0,
        color: str = "",
    ) -> TimePeriod:
        """创建一个时段"""
        period = TimePeriod(
            name=name,
            start_time=start_time,
            end_time=end_time,
            order_index=order_index,
            color=color,
        )
        self.session.add(period)
        self.session.commit()
        logger.info("创建时段 | id=%s name=%s", period.id, name)
        return period

    def update(self, period_id: str, **kwargs) -> bool:
        """更新时段字段；不允许改 id。"""
        period = self.get_by_id(period_id)
        if not period:
            return False
        for key, value in kwargs.items():
            if key == "id":
                continue
            if hasattr(period, key):
                setattr(period, key, value)
        self.session.commit()
        logger.info("更新时段 | id=%s | fields=%s", period_id, list(kwargs.keys()))
        return True

    def delete(self, period_id: str) -> bool:
        """删除时段。调用方负责把引用此 id 的任务的 time_period_id 置空。"""
        period = self.get_by_id(period_id)
        if not period:
            return False
        self.session.delete(period)
        self.session.commit()
        logger.info("删除时段 | id=%s name=%s", period_id, period.name)
        return True

    def reorder(self, ordered_ids: List[str]) -> bool:
        """根据传入 id 顺序重排 order_index。"""
        for index, period_id in enumerate(ordered_ids):
            period = self.get_by_id(period_id)
            if period is not None:
                period.order_index = index
        self.session.commit()
        return True

    def to_dict(self, period: TimePeriod) -> dict:
        """序列化时段"""
        return {
            "id": period.id,
            "name": period.name,
            "start_time": period.start_time or "",
            "end_time": period.end_time or "",
            "order_index": period.order_index or 0,
            "color": period.color or "",
            "created_at": period.created_at.isoformat() if period.created_at else "",
            "updated_at": period.updated_at.isoformat() if period.updated_at else "",
        }
