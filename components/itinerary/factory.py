"""行程组件工厂，集中管理组件装配。"""


class ItineraryComponentFactory:
    """延迟导入避免组件间循环依赖，并提供统一构造入口。"""

    @staticmethod
    def create_task_row(task_data, parent):
        from components.itinerary.task_row import ItineraryTaskRow
        return ItineraryTaskRow(task_data, parent)

    @staticmethod
    def create_hour_slot(hour, day_index, data_manager, main_window):
        from components.itinerary.hour_slot import HourSlotWidget
        return HourSlotWidget(hour, day_index, data_manager, main_window)

    @staticmethod
    def create_hour_block(start_hour, block_name, day_index, data_manager, main_window):
        from components.itinerary.views import HourBlockWidget
        return HourBlockWidget(start_hour, block_name, day_index, data_manager, main_window)

    @staticmethod
    def create_day_view(day_index, data_manager, main_window):
        from components.itinerary.views import DayViewWidget
        return DayViewWidget(day_index, data_manager, main_window)
