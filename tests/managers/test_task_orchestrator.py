"""Regression tests for task deletion cascading to itinerary records."""
from unittest.mock import MagicMock

import pytest

from managers.scheduling.itinerary_manager import ItineraryManager
from managers.tasks.daily_task_manager import DailyTaskManager
from managers.tasks.entertainment_task_manager import EntertainmentTaskManager
from managers.tasks.task_orchestrator import TaskOrchestrator
from managers.tasks.todo_task_manager import TodoTaskManager
from models.model import DailyTask, EntertainmentTask, ItineraryTask, TodoTask


@pytest.fixture
def task_orchestrator(db_session):
    trash = MagicMock()
    trash.move_to_trash.return_value = "trash-record-id"
    orchestrator = TaskOrchestrator(
        session=db_session,
        daily_task_manager=DailyTaskManager(db_session),
        todo_task_manager=TodoTaskManager(db_session),
        entertainment_task_manager=EntertainmentTaskManager(db_session),
        trash_manager=trash,
        itinerary_manager=ItineraryManager(db_session),
        task_limit_service_factory=MagicMock(),
    )
    return orchestrator, trash


@pytest.mark.parametrize(
    ("task_model", "task_type", "delete_method"),
    [
        (DailyTask, "daily", "delete_daily_task"),
        (TodoTask, "todo", "delete_todo_task"),
        (EntertainmentTask, "entertainment", "delete_entertainment_task"),
    ],
)
def test_single_task_delete_also_removes_all_itinerary_references(
    db_session, task_orchestrator, task_model, task_type, delete_method
):
    task = task_model(title="Task to delete")
    db_session.add(task)
    db_session.flush()
    db_session.add_all([
        ItineraryTask(title="Monday", task_id=task.id, task_type=task_type, day_of_week=1),
        ItineraryTask(title="Friday", task_id=task.id, task_type=task_type, day_of_week=5),
        ItineraryTask(title="Unrelated", task_id=task.id, task_type="todo", day_of_week=2),
    ])
    db_session.commit()

    orchestrator, trash = task_orchestrator
    assert getattr(orchestrator, delete_method)(task.id) is True

    assert db_session.get(task_model, task.id) is None
    assert db_session.query(ItineraryTask).filter_by(task_id=task.id, task_type=task_type).count() == 0
    assert db_session.query(ItineraryTask).filter_by(task_id=task.id, task_type="todo").count() == 1
    trash.move_to_trash.assert_called_once()


@pytest.mark.parametrize(
    ("task_model", "task_type", "delete_method"),
    [
        (DailyTask, "daily", "delete_daily_tasks_batch"),
        (TodoTask, "todo", "delete_todo_tasks_batch"),
        (EntertainmentTask, "entertainment", "delete_entertainment_tasks_batch"),
    ],
)
def test_batch_task_delete_removes_all_linked_itinerary_references(
    db_session, task_orchestrator, task_model, task_type, delete_method
):
    deleted_task = task_model(title="Delete me")
    retained_task = task_model(title="Keep me")
    db_session.add_all([deleted_task, retained_task])
    db_session.flush()
    db_session.add_all([
        ItineraryTask(title="Delete Monday", task_id=deleted_task.id, task_type=task_type, day_of_week=1),
        ItineraryTask(title="Delete Sunday", task_id=deleted_task.id, task_type=task_type, day_of_week=7),
        ItineraryTask(title="Keep", task_id=retained_task.id, task_type=task_type, day_of_week=3),
    ])
    db_session.commit()

    orchestrator, trash = task_orchestrator
    assert getattr(orchestrator, delete_method)([deleted_task.id]) == 1

    assert db_session.get(task_model, deleted_task.id) is None
    assert db_session.query(ItineraryTask).filter_by(task_id=deleted_task.id, task_type=task_type).count() == 0
    assert db_session.get(task_model, retained_task.id) is not None
    assert db_session.query(ItineraryTask).filter_by(task_id=retained_task.id, task_type=task_type).count() == 1
    trash.move_many_to_trash.assert_called_once()
