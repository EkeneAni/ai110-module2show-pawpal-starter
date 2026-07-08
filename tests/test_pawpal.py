"""Tests for PawPal+ core behaviors.

Grouped into happy paths (everything works as intended) and edge cases
(empty pets, exact-time clashes, running out of time). Run with:

    python -m pytest
"""

import os
import sys

# Make the project root importable when running `python -m pytest` from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta

from pawpal_system import Owner, Pet, Task, Priority, Recurrence, Scheduler


def _owner_with_tasks():
    """A small owner/pets/tasks fixture used across the scheduling tests.

    Biscuit: Evening walk @18:00 (30m, med), Morning walk @08:00 (30m, high).
    Mochi:   Feeding @08:15 (10m, high).
    Note Biscuit's tasks are added evening-first (out of chronological order).
    """
    owner = Owner(name="Jordan")
    dog = Pet(name="Biscuit", species="dog")
    cat = Pet(name="Mochi", species="cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    dog.add_task(Task("d1", "Evening walk", 30, Priority.MEDIUM, preferred_start_minute=18 * 60))
    dog.add_task(Task("d2", "Morning walk", 30, Priority.HIGH, preferred_start_minute=8 * 60))
    cat.add_task(Task("c1", "Feeding", 10, Priority.HIGH, preferred_start_minute=8 * 60 + 15))
    return owner, dog, cat


# --- happy paths -------------------------------------------------------------

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
    """sort_by_time() returns tasks chronologically regardless of input order."""
    _, dog, _ = _owner_with_tasks()
    ordered = Scheduler().sort_by_time(dog.tasks)  # dog tasks added evening-first
    assert [t.title for t in ordered] == ["Morning walk", "Evening walk"]


def test_filter_tasks_by_pet_and_status():
    """filter_tasks() narrows by pet name and by completion status."""
    owner, dog, _ = _owner_with_tasks()
    scheduler = Scheduler()

    mochi = scheduler.filter_tasks(owner, pet_name="Mochi")
    assert [t.title for _, t in mochi] == ["Feeding"]

    dog.tasks[1].mark_complete()  # complete Morning walk
    done = scheduler.filter_tasks(owner, completed=True)
    assert [t.title for _, t in done] == ["Morning walk"]


def test_completing_daily_task_queues_next_day():
    """Completing a DAILY task appends a fresh instance due one day later."""
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


def test_completing_weekly_task_queues_seven_days_later():
    """A WEEKLY task's next occurrence should be due seven days later."""
    pet = Pet(name="Biscuit", species="dog")
    pet.add_task(
        Task("bath", "Bath", 45, Priority.LOW,
             recurrence=Recurrence.WEEKLY, due_date=date(2026, 7, 7))
    )

    follow_up = pet.complete_task("bath")
    assert follow_up is not None
    assert follow_up.due_date == date(2026, 7, 7) + timedelta(days=7)


def test_detect_conflicts_flags_same_pet_overlap():
    """detect_conflicts() reports two of one pet's tasks that overlap in time."""
    owner, dog, _ = _owner_with_tasks()
    # Meds @08:15 overlaps the 08:00-08:30 morning walk.
    dog.add_task(Task("d3", "Meds", 10, Priority.HIGH, preferred_start_minute=8 * 60 + 15))

    warnings = Scheduler().detect_conflicts(owner)
    assert any("Morning walk" in w and "Meds" in w for w in warnings)


def test_detect_conflicts_flags_exact_same_time():
    """Two tasks at the exact same start time are flagged as a conflict."""
    owner = Owner(name="Jordan")
    dog = Pet(name="Biscuit", species="dog")
    owner.add_pet(dog)
    dog.add_task(Task("a", "Walk", 30, preferred_start_minute=8 * 60))
    dog.add_task(Task("b", "Feeding", 10, preferred_start_minute=8 * 60))  # same 08:00

    warnings = Scheduler().detect_conflicts(owner)
    assert len(warnings) == 1


# --- edge cases --------------------------------------------------------------

def test_sort_by_time_empty_list():
    """Sorting an empty task list returns an empty list (no crash)."""
    assert Scheduler().sort_by_time([]) == []


def test_schedule_pet_with_no_tasks():
    """A pet with no tasks yields an empty, non-crashing plan."""
    owner = Owner(name="Jordan")
    owner.add_pet(Pet(name="Ghost", species="cat"))

    plans = Scheduler().schedule(owner)
    assert plans["Ghost"].items == []
    assert plans["Ghost"].total_minutes == 0


def test_schedule_drops_task_when_over_budget():
    """When available time runs out, extra tasks land in `unscheduled`."""
    owner = Owner(name="Jordan", available_minutes=30)  # only room for one
    dog = Pet(name="Biscuit", species="dog")
    owner.add_pet(dog)
    dog.add_task(Task("keep", "Walk", 30, Priority.HIGH))
    dog.add_task(Task("drop", "Play", 20, Priority.LOW))

    plan = Scheduler().schedule(owner)["Biscuit"]
    assert [i.task.title for i in plan.items] == ["Walk"]
    assert [t.title for t in plan.unscheduled] == ["Play"]


def test_detect_conflicts_none_when_times_disjoint():
    """Tasks whose windows don't overlap produce no warnings."""
    owner = Owner(name="Jordan")
    dog = Pet(name="Biscuit", species="dog")
    owner.add_pet(dog)
    dog.add_task(Task("a", "Walk", 30, preferred_start_minute=8 * 60))     # 08:00-08:30
    dog.add_task(Task("b", "Dinner", 15, preferred_start_minute=18 * 60))  # 18:00-18:15

    assert Scheduler().detect_conflicts(owner) == []


def test_once_task_does_not_recur():
    """A ONCE task should not spawn a follow-up when completed."""
    pet = Pet(name="Biscuit", species="dog")
    pet.add_task(Task("vet", "Vet visit", 60, recurrence=Recurrence.ONCE))

    assert pet.complete_task("vet") is None
    assert len(pet.tasks) == 1
