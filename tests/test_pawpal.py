"""Tests for PawPal+ core behaviors."""

import os
import sys

# Make the project root importable when running `python -m pytest` from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import Pet, Task


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
