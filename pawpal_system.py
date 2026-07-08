"""PawPal+ logic layer.

I'm designing a pet care planning app around four core classes:

    - Task      : a single activity (description, duration, frequency,
                  completion status) that needs doing for a pet.
    - Pet       : stores pet details and owns a list of Tasks.
    - Owner     : manages multiple Pets and provides access to all of their
                  tasks in one place (plus the day-level time constraints).
    - Scheduler : the "brain" that retrieves tasks across pets, organizes them
                  by priority within the owner's time budget, and produces a
                  Plan per pet.

Supporting objects: Plan / ScheduledItem (the result) and the Priority /
Recurrence enums.

Times are integer minutes-from-midnight to keep scheduling math simple and
testable (08:00 == 480).

How the Scheduler talks to the Owner: it does NOT reach into `pet.tasks`
directly. It calls `Owner.all_tasks()`, which returns (pet, task) pairs across
every pet. That keeps the Owner the single source of truth for "what needs
doing" and lets the scheduler share one time budget across all pets.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import IntEnum, Enum


class Priority(IntEnum):
    """Task importance. IntEnum so tasks can be sorted directly by priority."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Recurrence(Enum):
    """How often a task repeats."""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


def _to_time_label(minute: int) -> str:
    """Convert minutes-from-midnight to 'HH:MM'."""
    minute = max(0, int(minute)) % (24 * 60)
    return f"{minute // 60:02d}:{minute % 60:02d}"


@dataclass
class Task:
    """One care activity for a pet."""

    id: str
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    recurrence: Recurrence = Recurrence.DAILY
    preferred_start_minute: int | None = None
    completed: bool = False
    due_date: date | None = None

    def update(self, **changes) -> None:
        """Apply field changes in place (used by Pet.edit_task).

        Unknown field names raise ValueError so a typo can't silently create a
        stray attribute.
        """
        for name, value in changes.items():
            if not hasattr(self, name):
                raise ValueError(f"Task has no field '{name}'")
            setattr(self, name, value)

    def mark_complete(self, done: bool = True) -> None:
        """Toggle completion status."""
        self.completed = done

    def next_occurrence(self) -> "Task | None":
        """Return a fresh, uncompleted Task for the next due date.

        DAILY advances one day, WEEKLY seven; a ONCE task doesn't repeat, so it
        returns None. The new due date is computed from this task's due_date
        (or today, if it has none) using timedelta for accurate calendar math.
        The id keeps a stable base and appends the new date so occurrences don't
        collide (e.g. 'walk' -> 'walk@2026-07-08').
        """
        if self.recurrence == Recurrence.ONCE:
            return None
        step = timedelta(days=1 if self.recurrence == Recurrence.DAILY else 7)
        base_date = self.due_date or date.today()
        new_due = base_date + step
        base_id = self.id.split("@")[0]
        return Task(
            id=f"{base_id}@{new_due.isoformat()}",
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            recurrence=self.recurrence,
            preferred_start_minute=self.preferred_start_minute,
            completed=False,
            due_date=new_due,
        )


@dataclass
class Pet:
    """A pet plus the tasks its owner wants done for it."""

    name: str
    species: str
    breed: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's list (rejects duplicate ids)."""
        if any(t.id == task.id for t in self.tasks):
            raise ValueError(f"Task id '{task.id}' already exists for {self.name}")
        self.tasks.append(task)

    def _find(self, task_id: str) -> Task:
        """Return the task with this id, or raise KeyError if absent."""
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise KeyError(f"No task '{task_id}' for pet {self.name}")

    def edit_task(self, task_id: str, **changes) -> Task:
        """Find the task by id, apply changes, and return the updated task."""
        task = self._find(task_id)
        task.update(**changes)
        return task

    def remove_task(self, task_id: str) -> None:
        """Remove the task with the given id."""
        self._find(task_id)  # raises if missing
        self.tasks = [t for t in self.tasks if t.id != task_id]

    def complete_task(self, task_id: str) -> Task | None:
        """Mark a task complete and, if it recurs, queue its next occurrence.

        Returns the newly created follow-up Task (for DAILY/WEEKLY tasks) or
        None (for ONCE tasks, or if the next occurrence already exists).
        """
        task = self._find(task_id)
        task.mark_complete(True)
        follow_up = task.next_occurrence()
        if follow_up is None or any(t.id == follow_up.id for t in self.tasks):
            return None
        self.tasks.append(follow_up)
        return follow_up

    def pending_tasks(self) -> list[Task]:
        """Tasks not yet completed."""
        return [t for t in self.tasks if not t.completed]


@dataclass
class Owner:
    """The pet owner: manages pets and the day-level scheduling constraints."""

    name: str
    day_start_minute: int = 8 * 60      # 08:00
    day_end_minute: int = 21 * 60       # 21:00
    available_minutes: int = 120        # total time the owner can give today
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def available_window(self) -> tuple[int, int]:
        """Return (day_start_minute, day_end_minute)."""
        return (self.day_start_minute, self.day_end_minute)

    def all_tasks(self, include_completed: bool = False) -> list[tuple[Pet, Task]]:
        """Every task across every pet, as (pet, task) pairs.

        This is how the Scheduler retrieves work without reaching into each
        Pet's internals. Completed tasks are excluded by default.
        """
        pairs: list[tuple[Pet, Task]] = []
        for pet in self.pets:
            for task in pet.tasks:
                if include_completed or not task.completed:
                    pairs.append((pet, task))
        return pairs


@dataclass
class ScheduledItem:
    """A task placed at a concrete time, with a reason for the 'explain' view."""

    task: Task
    start_minute: int
    end_minute: int
    reason: str = ""

    def time_label(self) -> str:
        """Human-readable start time, e.g. '08:00'."""
        return _to_time_label(self.start_minute)


@dataclass
class Plan:
    """The scheduling result for a single pet."""

    pet: Pet
    items: list[ScheduledItem] = field(default_factory=list)
    unscheduled: list[Task] = field(default_factory=list)
    total_minutes: int = 0

    def summary(self) -> str:
        """Render the plan (and why) as display text."""
        lines = [f"Daily plan for {self.pet.name} ({self.pet.species}):"]
        if not self.items:
            lines.append("  (nothing scheduled)")
        for item in self.items:
            lines.append(
                f"  {item.time_label()} — {item.task.title} "
                f"({item.task.duration_minutes} min) "
                f"[priority: {item.task.priority.name.lower()}]"
            )
            if item.reason:
                lines.append(f"      ↳ {item.reason}")
        if self.unscheduled:
            names = ", ".join(t.title for t in self.unscheduled)
            lines.append(f"  Not scheduled (ran out of time): {names}")
        lines.append(f"  Total planned time: {self.total_minutes} min")
        return "\n".join(lines)


class Scheduler:
    """Stateless planner: turns an owner's pets + constraints into per-pet Plans."""

    def schedule(self, owner: Owner) -> dict[str, Plan]:
        """Build a daily plan for each of the owner's pets.

        Pending tasks are gathered across all pets, sorted by priority, and
        packed into a single shared timeline bounded by the owner's waking
        window and total available minutes. Placed tasks are then grouped back
        into a Plan per pet; anything that didn't fit lands in that pet's
        `unscheduled` list. Returns a dict keyed by pet name.
        """
        day_start, day_end = owner.available_window()

        # 1. Retrieve tasks across pets (via the Owner) and order them.
        pairs = self._sort_pairs(owner.all_tasks())

        # 2. Greedily pack into the shared timeline / time budget.
        plans: dict[str, Plan] = {pet.name: Plan(pet=pet) for pet in owner.pets}
        cursor = day_start
        remaining = owner.available_minutes

        for pet, task in pairs:
            plan = plans[pet.name]
            start = cursor
            if (
                task.preferred_start_minute is not None
                and task.preferred_start_minute >= cursor
            ):
                start = task.preferred_start_minute
            end = start + task.duration_minutes

            if task.duration_minutes <= remaining and end <= day_end:
                plan.items.append(
                    ScheduledItem(
                        task=task,
                        start_minute=start,
                        end_minute=end,
                        reason=self._reason(task, start),
                    )
                )
                plan.total_minutes += task.duration_minutes
                cursor = end
                remaining -= task.duration_minutes
            else:
                plan.unscheduled.append(task)

        return plans

    def _sort_pairs(
        self, pairs: list[tuple[Pet, Task]]
    ) -> list[tuple[Pet, Task]]:
        """Highest priority first; then honor earlier preferred times; then
        shorter tasks (so quick, important care isn't blocked by a long one)."""
        return sorted(
            pairs,
            key=lambda pt: (
                -int(pt[1].priority),
                pt[1].preferred_start_minute
                if pt[1].preferred_start_minute is not None
                else 24 * 60,
                pt[1].duration_minutes,
            ),
        )

    def _reason(self, task: Task, start_minute: int) -> str:
        """Explain why the task landed where it did."""
        why = f"{task.priority.name.lower()} priority"
        if task.preferred_start_minute is not None and start_minute == task.preferred_start_minute:
            why += f", placed at preferred time {_to_time_label(start_minute)}"
        else:
            why += ", placed in the next open slot"
        return why

    # --- sorting / filtering / conflict detection ----------------------------

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return the tasks ordered by preferred start time (earliest first).

        Because times are stored as integer minutes-from-midnight, a single
        lambda key sorts them directly — no 'HH:MM' string parsing needed.
        Tasks with no preferred time sort to the end.
        """
        return sorted(
            tasks,
            key=lambda t: t.preferred_start_minute
            if t.preferred_start_minute is not None
            else 24 * 60,
        )

    def filter_tasks(
        self,
        owner: Owner,
        *,
        pet_name: str | None = None,
        completed: bool | None = None,
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs matching the given filters.

        pet_name  -> only tasks belonging to that pet (None = all pets).
        completed -> True for done tasks, False for pending, None for either.
        """
        result: list[tuple[Pet, Task]] = []
        for pet, task in owner.all_tasks(include_completed=True):
            if pet_name is not None and pet.name != pet_name:
                continue
            if completed is not None and task.completed != completed:
                continue
            result.append((pet, task))
        return result

    def detect_conflicts(self, owner: Owner) -> list[str]:
        """Find pending tasks whose preferred time windows overlap.

        Lightweight: compares every pair of tasks that have a preferred start
        time and returns a list of human-readable warning strings (empty if
        there are none). It never raises — a clash is reported, not fatal.
        """
        timed = [
            (pet, task)
            for pet, task in owner.all_tasks()
            if task.preferred_start_minute is not None
        ]
        warnings: list[str] = []
        # itertools.combinations gives every unique task pair once, without the
        # manual index bookkeeping of a nested range() loop.
        for (pet_a, task_a), (pet_b, task_b) in itertools.combinations(timed, 2):
            start_a, start_b = task_a.preferred_start_minute, task_b.preferred_start_minute
            end_a = start_a + task_a.duration_minutes
            end_b = start_b + task_b.duration_minutes
            if start_a < end_b and start_b < end_a:  # windows overlap
                who = (
                    pet_a.name
                    if pet_a.name == pet_b.name
                    else f"{pet_a.name} and {pet_b.name}"
                )
                warnings.append(
                    f"⚠ Conflict for {who}: "
                    f"'{task_a.title}' ({_to_time_label(start_a)}) overlaps "
                    f"'{task_b.title}' ({_to_time_label(start_b)})"
                )
        return warnings
