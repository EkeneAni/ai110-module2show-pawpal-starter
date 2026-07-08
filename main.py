"""PawPal+ terminal demo / testing ground.

Wires the pawpal_system classes together and prints today's schedule so you can
verify the logic runs from the terminal:  python main.py
"""

import sys

# The schedule summary uses a '↳' glyph; the default Windows console (cp1252)
# can't encode it, so switch stdout to UTF-8 when possible.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pawpal_system import Owner, Pet, Task, Priority, Scheduler


def build_owner() -> Owner:
    """Create an owner with two pets and a handful of tasks at different times."""
    owner = Owner(name="Jordan", day_start_minute=8 * 60, day_end_minute=21 * 60,
                  available_minutes=120)

    biscuit = Pet(name="Biscuit", species="dog", breed="Golden Retriever")
    mochi = Pet(name="Mochi", species="cat")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)

    # Three-plus tasks, each with a different preferred time / priority.
    biscuit.add_task(Task("b1", "Morning walk", 30, Priority.HIGH,
                          preferred_start_minute=8 * 60))          # 08:00
    biscuit.add_task(Task("b2", "Enrichment play", 20, Priority.LOW,
                          preferred_start_minute=17 * 60))         # 17:00
    mochi.add_task(Task("m1", "Feeding", 10, Priority.HIGH,
                        preferred_start_minute=8 * 60 + 30))       # 08:30
    mochi.add_task(Task("m2", "Litter clean", 15, Priority.MEDIUM,
                        preferred_start_minute=12 * 60))           # 12:00

    return owner


def main() -> None:
    """Build the demo data, run the scheduler, and print today's schedule."""
    owner = build_owner()
    plans = Scheduler().schedule(owner)

    print("=" * 44)
    print(f"Today's Schedule for {owner.name}")
    print("=" * 44)
    for plan in plans.values():
        print()
        print(plan.summary())


if __name__ == "__main__":
    main()
