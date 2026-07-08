# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Sample of the CLI output from running `python main.py`:

```
====================================================
Today's Schedule for Jordan
====================================================

Daily plan for Biscuit (dog):
  08:00 — Feeding (10 min) [priority: high]
      ↳ high priority, placed at preferred time 08:00
  08:10 — Morning walk (30 min) [priority: high]
      ↳ high priority, placed in the next open slot
  18:00 — Evening walk (30 min) [priority: medium]
      ↳ medium priority, placed at preferred time 18:00
  Total planned time: 70 min

Daily plan for Mochi (cat):
  08:40 — Feeding (10 min) [priority: high]
      ↳ high priority, placed in the next open slot
  12:00 — Litter clean (15 min) [priority: medium]
      ↳ medium priority, placed at preferred time 12:00
  Total planned time: 25 min

----------------------------------------------------
Sorted by time (Biscuit):
  08:00  Morning walk     ( 30 min)  high   [pending]
  08:00  Feeding          ( 10 min)  high   [pending]
  18:00  Evening walk     ( 30 min)  medium [pending]

----------------------------------------------------
Conflict check:
  ⚠ Conflict for Biscuit: 'Morning walk' (08:00) overlaps 'Feeding' (08:00)

----------------------------------------------------
Recurring tasks:
  Completing Biscuit's daily 'Morning walk'...
  -> queued next occurrence: id='b_walk@2026-07-08', due 2026-07-08

----------------------------------------------------
Filtering:
  Completed tasks:
    [Biscuit] 08:00  Morning walk     ( 30 min)  high   [done]
  Mochi's pending tasks:
    [Mochi] 12:00  Litter clean     ( 15 min)  medium [pending]
    [Mochi] 08:30  Feeding          ( 10 min)  high   [pending]
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time`, `Scheduler._sort_pairs` | Times are stored as integer minutes-from-midnight, so a single `sorted()` lambda key orders tasks — no `HH:MM` string parsing. The scheduler itself sorts by priority, then preferred time, then duration. |
| Filtering | `Scheduler.filter_tasks`, `Owner.all_tasks`, `Pet.pending_tasks` | Filter `(pet, task)` pairs by `pet_name` and/or `completed` status. |
| Conflict handling | `Scheduler.detect_conflicts` | Pairwise overlap check on preferred time windows; returns human-readable warnings (never raises), covering same-pet and cross-pet clashes. |
| Recurring tasks | `Task.next_occurrence`, `Pet.complete_task`, `Recurrence` enum | Completing a `DAILY`/`WEEKLY` task auto-queues the next instance, advancing `due_date` with `timedelta` (+1 or +7 days). `ONCE` tasks don't recur. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
