"""行程组件兼容入口。"""

from components.itinerary.hour_slot import HourSlotWidget
from components.itinerary.payload import parse_task_payload
from components.itinerary.task_row import ItineraryTaskRow
from components.itinerary.views import DayViewWidget, HourBlockWidget
from components.itinerary.widget import ItineraryWidget

_parse_task_payload = parse_task_payload

__all__ = ['DayViewWidget', 'HourBlockWidget', 'HourSlotWidget', 'ItineraryTaskRow', 'ItineraryWidget', '_parse_task_payload']
