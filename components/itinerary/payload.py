"""行程拖拽载荷的兼容解析。"""

import json

from components.itinerary.constants import STATUS_TO_KEY
from managers.tasks.priority import DEFAULT_PRIORITY, LABEL_TO_KEY


def parse_task_payload(raw: str) -> dict:
    """解析 JSON 载荷，并兼容历史的竖线分隔格式。"""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data.setdefault('status', '○')
            data.setdefault('priority_key', LABEL_TO_KEY.get(data.get('priority', ''), DEFAULT_PRIORITY))
            data.setdefault('status_key', STATUS_TO_KEY.get(data['status'], 'pending'))
            return data
    except (TypeError, ValueError):
        pass
    parts = raw.split('|')
    if len(parts) < 2:
        return {}
    priority = parts[5] if len(parts) > 5 else '普通'
    status = parts[2] if len(parts) > 2 else '○'
    return {
        'task_id': parts[0],
        'task_type': parts[1],
        'status': status,
        'status_key': STATUS_TO_KEY.get(status, 'pending'),
        'title': parts[3] if len(parts) > 3 else f'任务 {parts[0][:8]}...',
        'tags': parts[4] if len(parts) > 4 else '',
        'priority': priority,
        'priority_key': LABEL_TO_KEY.get(priority, DEFAULT_PRIORITY),
    }
