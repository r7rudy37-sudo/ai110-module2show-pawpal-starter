"""Behavioral tests for multi-pet scheduling and persistence."""
from datetime import date, datetime, timedelta
import json

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task, load_owner, save_owner


@pytest.fixture
def household():
    owner = Owner("Jordan", [Pet("Mochi", "dog"), Pet("Luna", "cat")])
    return owner, Scheduler(owner)


def at(hour=8, minute=0, day=26):
    return datetime(2026, 10, day, hour, minute)


def test_sort_collects_both_pets_without_mutating(household):
    owner, scheduler = household
    late, early = Task("Walk", at(18)), Task("Feed", at(8))
    owner.pets[0].add_task(late)
    owner.pets[1].add_task(early)
    assert scheduler.sort_by_time() == [early, late]
    assert owner.get_all_tasks() == [late, early]
    assert scheduler.sort_by_time([]) == []


def test_filters_pet_status_and_date(household):
    owner, scheduler = household
    first = Task("Walk", at(), completed=True)
    second = Task("Feed", at())
    third = Task("Brush", at(day=27))
    owner.pets[0].add_task(first)
    owner.pets[1].add_task(second)
    owner.pets[1].add_task(third)
    assert scheduler.filter_tasks(owner.pets[1].id, False, date(2026, 10, 26)) == [second]
    assert scheduler.filter_tasks(completed=True) == [first]


@pytest.mark.parametrize("frequency,days", [("daily", 1), ("weekly", 7)])
def test_recurrence_completes_once_with_new_id(household, frequency, days):
    owner, scheduler = household
    task = Task("Feed", datetime(2026, 12, 31, 8), 10, "high", frequency)
    owner.pets[1].add_task(task)
    next_task = scheduler.mark_task_complete(task.id)
    assert task.completed and not next_task.completed
    assert next_task.due == task.due + timedelta(days=days)
    assert next_task.pet_id == task.pet_id
    assert next_task.id != task.id
    assert (next_task.description, next_task.priority, next_task.duration_minutes) == ("Feed", "high", 10)
    assert scheduler.mark_task_complete(task.id) is None
    assert len(owner.get_all_tasks()) == 2


def test_one_off_completion_and_missing_task(household):
    owner, scheduler = household
    task = Task("Vet", at())
    owner.pets[0].add_task(task)
    assert scheduler.mark_task_complete(task.id) is None
    assert task.completed and len(owner.get_all_tasks()) == 1
    with pytest.raises(ValueError, match="not found"):
        scheduler.mark_task_complete("missing")


def test_conflicts_across_and_within_pets_and_boundaries(household):
    owner, scheduler = household
    owner.pets[0].add_task(Task("Walk", at(), 30))
    owner.pets[1].add_task(Task("Feed", at(), 10))
    owner.pets[0].add_task(Task("Meds", at(8, 20), 5))
    owner.pets[1].add_task(Task("Brush", at(8, 30), 10))
    owner.pets[1].add_task(Task("Done", at(), completed=True))
    warnings = scheduler.detect_conflicts()
    assert len(warnings) == 2
    assert "Mochi" in warnings[0] and "Luna" in warnings[0]
    assert not scheduler.detect_conflicts(date(2026, 10, 27))


def test_conflict_crossing_midnight(household):
    owner, scheduler = household
    owner.pets[0].add_task(Task("Late walk", at(23, 50), 30))
    owner.pets[1].add_task(Task("Early feeding", at(0, 5, 27), 10))
    assert len(scheduler.detect_conflicts(date(2026, 10, 27))) == 1
    assert not scheduler.detect_conflicts(date(2026, 10, 26))


def test_plan_priority_moves_lower_task_and_reports_unfit(household):
    owner, scheduler = household
    low = Task("Brush", at(), 20, "low")
    high = Task("Feed", at(), 10, "high")
    late = Task("Walk", at(18), 30)
    owner.pets[0].add_task(low)
    owner.pets[1].add_task(high)
    owner.pets[0].add_task(late)
    plan = scheduler.build_plan(date(2026, 10, 26), at(), at(9))
    assert [block["task"] for block in plan["scheduled"]] == [high, low]
    assert plan["scheduled"][1]["start"] == at(8, 10)
    assert plan["scheduled"][0]["end"] <= plan["scheduled"][1]["start"]
    assert plan["skipped"][0]["task"] is late
    assert low.due == at()  # Planning must not change preferred times.


def test_plan_fills_gap_and_exact_end(household):
    owner, scheduler = household
    owner.pets[0].add_task(Task("High", at(9), 30, "high"))
    owner.pets[1].add_task(Task("Low", at(8), 60, "low"))
    plan = scheduler.build_plan(date(2026, 10, 26), at(8), at(9, 30))
    assert [(block["start"], block["end"]) for block in plan["scheduled"]] == [(at(8), at(9)), (at(9), at(9, 30))]
    assert not plan["skipped"]


def test_empty_household_and_invalid_window(household):
    _, scheduler = household
    assert scheduler.sort_by_time() == []
    assert scheduler.detect_conflicts() == []
    assert scheduler.build_plan(date(2026, 10, 26), at(), at(9)) == {"scheduled": [], "skipped": []}
    with pytest.raises(ValueError):
        scheduler.build_plan(date(2026, 10, 26), at(9), at())


@pytest.mark.parametrize("changes", [{"description": " "}, {"duration_minutes": -1}, {"duration_minutes": "ten"}, {"duration_minutes": True}, {"priority": "urgent"}, {"frequency": "monthly"}, {"due": "08:00"}, {"completed": "yes"}])
def test_invalid_task_inputs(changes):
    values = {"description": "Walk", "due": at()}
    values.update(changes)
    with pytest.raises(ValueError):
        Task(**values)


def test_edit_is_validated_before_change(household):
    owner, scheduler = household
    task = Task("Walk", at())
    owner.pets[0].add_task(task)
    with pytest.raises(ValueError):
        scheduler.update_task(task.id, duration_minutes=0)
    assert owner.get_all_tasks()[0].duration_minutes == 15
    updated = scheduler.update_task(task.id, description="Long walk", duration_minutes=30)
    assert updated.id == task.id and updated.description == "Long walk"
    scheduler.mark_task_complete(updated.id)
    with pytest.raises(ValueError):
        scheduler.update_task(updated.id, priority="low")


def test_same_pet_name_uses_stable_ids(household):
    owner, scheduler = household
    owner.pets[1].name = owner.pets[0].name
    task = Task("Feed", at())
    owner.pets[1].add_task(task)
    assert scheduler.filter_tasks(pet_id=owner.pets[0].id) == []
    assert scheduler.filter_tasks(pet_id=owner.pets[1].id) == [task]
    with pytest.raises(ValueError):
        owner.pets[0].add_task(task)


def test_json_roundtrip_preserves_occurrences_and_completion(household, tmp_path):
    owner, scheduler = household
    task = Task("Feed", at(), frequency="daily")
    owner.pets[1].add_task(task)
    scheduler.mark_task_complete(task.id)
    path = tmp_path / "nested" / "care.json"
    save_owner(owner, path)
    restored = load_owner(path)
    assert restored == owner
    assert isinstance(restored.get_all_tasks()[0].due, datetime)
    assert not path.with_suffix(".json.tmp").exists()


@pytest.mark.parametrize("content", ["not json", '{"version": 9}', '{"version":1,"owner":{}}'])
def test_malformed_save_is_rejected(tmp_path, content):
    path = tmp_path / "care.json"
    path.write_text(content)
    with pytest.raises(ValueError, match="Invalid PawPal save"):
        load_owner(path)
    assert path.read_text() == content
