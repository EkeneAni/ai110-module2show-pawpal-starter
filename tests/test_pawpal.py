"""Tests for PawPal+ core behaviors."""

import os
import sys

# Make the project root importable when running `python -m pytest` from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta

from pawpal_system import Owner, Pet, Task, Priority, Recurrence, Scheduler


def _owner_with_tasks():
    """A small owner/pets/tasks fixture used by the smarter-scheduling tests."""
    owner = Owner(name="Jordan")
    dog = Pet(name="Biscuit", species="dog")
    cat = Pet(name="Mochi", species="cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    dog.add_task(Task("d1", "Evening walk", 30, Priority.MEDIUM, preferred_start_minute=18 * 60))
    dog.add_task(Task("d2", "Morning walk", 30, Priority.HIGH, preferred_start_minute=8 * 60))
    cat.add_task(Task("c1", "Feeding", 10, Priority.HIGH, preferred_start_minute=8 * 60 + 15))
    return owner, dog, cat


def test_mark_complete_changes_status():
    """mark_complete() should flip a task's completion status."""
    task = Task(id="t1", title="Morning walk", duration_minutes=30)
    assert task.completed is False

    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet should increase that pet's task count."""
    pet = Pet(name="Biscuit", species="dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task(id="t1", title="Feeding", duration_minutes=10))
    assert len(pet.tasks) == 1


def test_sort_by_time_orders_by_preferred_start():
    """sort_by_time() should return tasks earliest-first regardless of input order."""
    _, dog, _ = _owner_with_tasks()
    ordered = Scheduler().sort_by_time(dog.tasks)  # dog tasks added evening-first
    assert [t.title for t in ordered] == ["Morning walk", "Evening walk"]


def test_filter_tasks_by_pet_and_status():
    """filter_tasks() should narrow by pet name and by completion status."""
    owner, dog, _ = _owner_with_tasks()
    scheduler = Scheduler()

    mochi = scheduler.filter_tasks(owner, pet_name="Mochi")
    assert [t.title for _, t in mochi] == ["Feeding"]

    dog.tasks[1].mark_complete()  # complete Morning walk
    done = scheduler.filter_tasks(owner, completed=True)
    assert [t.title for _, t in done] == ["Morning walk"]


def test_completing_daily_task_queues_next_occurrence():
    """Completing a DAILY task should append a fresh instance due one day later."""
    pet = Pet(name="Biscuit", species="dog")
    pet.add_task(
        Task("walk", "Morning walk", 30, Priority.HIGH,
             recurrence=Recurrence.DAILY, due_date=date(2026, 7, 7))
    )

    follow_up = pet.complete_task("walk")
    assert follow_up is not None
    assert follow_up.completed is False
    assert follow_up.due_date == date(2026, 7, 7) + timedelta(days=1)
    assert len(pet.tasks) == 2  # original (done) + next occurrence


def test_once_task_does_not_recur():
    """A ONCE task should not spawn a follow-up when completed."""
    pet = Pet(name="Biscuit", species="dog")
    pet.add_task(Task("vet", "Vet visit", 60, recurrence=Recurrence.ONCE))

    assert pet.complete_task("vet") is None
    assert len(pet.tasks) == 1


def test_detect_conflicts_flags_overlap():
    """detect_conflicts() should report overlapping preferred windows, not crash."""
    owner, dog, _ = _owner_with_tasks()
    # Add a task that overlaps the 08:00 morning walk (08:00-08:30).
    dog.add_task(Task("d3", "Meds", 10, Priority.HIGH, preferred_start_minute=8 * 60 + 15))

    warnings = Scheduler().detect_conflicts(owner)
    assert any("Morning walk" in w and "Meds" in w for w in warnings)


def test_detect_conflicts_empty_when_no_overlap():
    """Non-overlapping tasks should produce no conflict warnings."""
    owner, _, _ = _owner_with_tasks()  # 18:00, 08:00, 08:15 -> walk & feeding overlap? no
    # Fixture: Evening 18:00 (30m), Morning 08:00 (30m), cat Feeding 08:15 (10m).
    # Morning 08:00-08:30 overlaps cat Feeding 08:15-08:25 across pets -> expect 1.
    warnings = Scheduler().detect_conflicts(owner)
    assert len(warnings) == 1
