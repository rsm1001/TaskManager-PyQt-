"""
已安排行程过滤测试
"""
from main import TaskManagerMainWindow
from managers.itinerary_manager import ItineraryManager
from models.model import ItineraryTask


def test_itinerary_refs_can_be_filtered_by_weekday(db_session):
    """只返回指定星期已安排的任务引用。"""
    db_session.add_all([
        ItineraryTask(title='周一任务', task_id='monday', task_type='daily', day_of_week=1),
        ItineraryTask(title='周二任务', task_id='tuesday', task_type='daily', day_of_week=2),
        ItineraryTask(title='周二手动行程', day_of_week=2),
    ])
    db_session.commit()

    refs = ItineraryManager(db_session).get_task_refs(day_of_week=2)

    assert refs == {('daily', 'tuesday')}


def test_weekday_change_refreshes_all_filtered_tables():
    """过滤开启时切换星期刷新缓存和三个任务表。"""
    calls = []
    window = type('Window', (), {
        'filter_arranged_tasks': True,
        '_refresh_arranged_cache': lambda self: calls.append('cache'),
        'load_daily_tasks': lambda self: calls.append('daily'),
        'load_todo_tasks': lambda self: calls.append('todo'),
        'load_entertainment_tasks': lambda self: calls.append('entertainment'),
    })()

    TaskManagerMainWindow.load_tasks_for_selected_weekday(window)

    assert calls == ['cache', 'todo', 'entertainment', 'daily']


def test_refresh_arranged_cache_uses_selected_weekday():
    """缓存按主界面当前星期读取行程。"""
    requested = []

    class DataManager:
        def get_itinerary_task_refs(self, **kwargs):
            requested.append(kwargs['day_of_week'])
            return {('daily', '任务一')}

    class WeekdayCombo:
        def currentText(self):
            return '星期三'

    window = type('Window', (), {
        'daily_weekday_combo': WeekdayCombo(),
        'data_manager': DataManager(),
    })()

    TaskManagerMainWindow._refresh_arranged_cache(window)

    assert requested == [3]
    assert window._arranged_task_refs == {('daily', '任务一')}
