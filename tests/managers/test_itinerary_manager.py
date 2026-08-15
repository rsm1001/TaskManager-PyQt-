from __future__ import annotations

import json

from managers.scheduling.itinerary_manager import ItineraryManager
from models.model import ItineraryTask


def test_clear_shortcut_bindings_removes_persisted_binding_metadata(db_session):
    bound = ItineraryTask(
        title="Bound task",
        task_id="task-1",
        task_type="todo",
        description=json.dumps({
            "task_id": "task-1",
            "shortcut_id": "shortcut-1",
            "shortcut_title": "Launch me",
            "shortcut_path": "C:/launch-me.ps1",
            "shortcut_action_type": "script",
            "status": "○",
        }, ensure_ascii=False),
    )
    unrelated = ItineraryTask(
        title="Unrelated task",
        task_id="task-2",
        task_type="todo",
        description=json.dumps({"shortcut_id": "shortcut-2", "shortcut_title": "Keep me"}),
    )
    legacy = ItineraryTask(title="Legacy", task_type="shortcut", description="not-json")
    db_session.add_all([bound, unrelated, legacy])
    db_session.commit()

    assert ItineraryManager(db_session).clear_shortcut_bindings("shortcut-1") == 1

    db_session.expire_all()
    payload = json.loads(db_session.get(ItineraryTask, bound.id).description)
    assert "shortcut_id" not in payload
    assert "shortcut_title" not in payload
    assert "shortcut_path" not in payload
    assert "shortcut_action_type" not in payload
    assert payload["status"] == "○"
    assert json.loads(db_session.get(ItineraryTask, unrelated.id).description)["shortcut_id"] == "shortcut-2"
    assert db_session.get(ItineraryTask, legacy.id).description == "not-json"
