"""PawPal+ terminal demo / testing ground.

Wires the pawpal_system classes together and exercises the "smarter scheduling"
features from the terminal:  python main.py

    - a daily schedule (priority-packed, explained)
    - sorting tasks by time
    - filtering tasks by pet / completion status
    - recurring tasks (completing a daily task queues the next occurrence)
    - lightweight conflict detection
"""

import sys

# The schedule summary uses a '↳' glyph; the default Windows console (cp1252)
# can't encode it, so switch stdout to UTF-8 when possible.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pawpal_system import Owner, Pet, Task, Priority, Recurrence, Scheduler, _to_time_label


def _fmt(task: Task) -> str:
    """One-line description of a task for the demo output."""
    when = _to_time_label(task.preferred_start_minute) if task.preferred_start_minute is not None else "--:--"
    status = "done" if task.completed else "pending"
    return f"{when}  {task.title:<16} ({task.duration_minutes:>3} min)  {task.priority.name.lower():<6} [{status}]"


def build_owner() -> Owner:
    """Create an owner with two pets and tasks added deliberately out of order."""
    owner = Owner(name="Jordan", day_start_minute=8 * 60, day_end_minute=21 * 60,
                  available_minutes=120)

    biscuit = Pet(name="Biscuit", species="dog", breed="Golden Retriever")
    mochi = Pet(name="Mochi", species="cat")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)

    # Added out of chronological order on purpose (evening before morning) so
    # the sort_by_time demo has something to fix.
    biscuit.add_task(Task("b_eve", "Evening walk", 30, Priority.MEDIUM,
                          preferred_start_minute=18 * 60))          # 18:00
    biscuit.add_task(Task("b_walk", "Morning walk", 30, Priority.HIGH,
                          recurrence=Recurrence.DAILY,
                          preferred_start_minute=8 * 60))           # 08:00
    # Same-pet clash with Morning walk (08:00) -> conflict detection target.
    biscuit.add_task(Task("b_feed", "Feeding", 10, Priority.HIGH,
                          preferred_start_minute=8 * 60))           # 08:00

    mochi.add_task(Task("m_litter", "Litter clean", 15, Priority.MEDIUM,
                        preferred_start_minute=12 * 60))            # 12:00
    mochi.add_task(Task("m_feed", "Feeding", 10, Priority.HIGH,
                        recurrence=Recurrence.DAILY,
                        preferred_start_minute=8 * 60 + 30))        # 08:30

    return owner


def show_schedule(owner: Owner, scheduler: Scheduler) -> None:
    """Section 1: the generated daily plan per pet."""
    print("=" * 52)
    print(f"Today's Schedule for {owner.name}")
    print("=" * 52)
    for plan in scheduler.schedule(owner).values():
        print()
        print(plan.summary())


def show_sorting(owner: Owner, scheduler: Scheduler) -> None:
    """Section 2: Biscuit's tasks sorted by time (they were added out of order)."""
    print("\n" + "-" * 52)
    print("Sorted by time (Biscuit):")
    biscuit = owner.pets[0]
    for task in scheduler.sort_by_time(biscuit.tasks):
        print("  " + _fmt(task))


def show_conflicts(owner: Owner, scheduler: Scheduler) -> None:
    """Section 3: overlapping preferred times."""
    print("\n" + "-" * 52)
    print("Conflict check:")
    conflicts = scheduler.detect_conflicts(owner)
    if conflicts:
        for warning in conflicts:
            print("  " + warning)
    else:
        print("  No conflicts found.")


def show_recurrence(owner: Owner) -> None:
    """Section 4: completing a daily task queues its next occurrence."""
    print("\n" + "-" * 52)
    print("Recurring tasks:")
    biscuit = owner.pets[0]
    print("  Completing Biscuit's daily 'Morning walk'...")
    follow_up = biscuit.complete_task("b_walk")
    if follow_up is not None:
        print(f"  -> queued next occurrence: id='{follow_up.id}', due {follow_up.due_date}")
    else:
        print("  -> no follow-up created")


def show_filtering(owner: Owner, scheduler: Scheduler) -> None:
    """Section 5: filter by completion status and by pet."""
    print("\n" + "-" * 52)
    print("Filtering:")

    done = scheduler.filter_tasks(owner, completed=True)
    print("  Completed tasks:")
    for pet, task in done:
        print(f"    [{pet.name}] " + _fmt(task))

    mochi_tasks = scheduler.filter_tasks(owner, pet_name="Mochi")
    print("  Mochi's pending tasks:")
    for pet, task in mochi_tasks:
        print(f"    [{pet.name}] " + _fmt(task))


def main() -> None:
    """Build the demo data and run each feature section."""
    owner = build_owner()
    scheduler = Scheduler()

    show_schedule(owner, scheduler)
    show_sorting(owner, scheduler)
    show_conflicts(owner, scheduler)
    show_recurrence(owner)       # mutates: completes a task, adds its next occurrence
    show_filtering(owner, scheduler)


if __name__ == "__main__":
    main()
