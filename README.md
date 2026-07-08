# PawPal+ (Module 2 Project)

**PawPal+** is a Streamlit app that helps a busy pet owner plan care tasks for their pets.
Enter your pets and their tasks, and PawPal+ builds a prioritized daily plan — placing the
most important care first within the time you have, flagging clashes, and explaining every
choice.

## Scenario

A busy pet owner needs help staying consistent with pet care. PawPal+:

- Tracks pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Considers constraints (time available, priority, preferred times)
- Produces a daily plan and explains why it chose that plan

The system was designed UML-first, implemented as a Python logic layer (`pawpal_system.py`),
and connected to a Streamlit UI (`app.py`), with a CLI demo (`main.py`) and a pytest suite.

## Features

- **Owner & pets** — enter owner info and daily time budget; add multiple pets, each with its own tasks.
- **Add / edit / remove tasks** — title, duration, priority (low/medium/high), and an optional preferred start time. (`Pet.add_task`, `Pet.edit_task`, `Pet.remove_task`)
- **Priority-based daily plan** — a greedy scheduler packs tasks (highest priority first, then earliest preferred time, then shortest) into the owner's waking window and time budget, and explains each placement. (`Scheduler.schedule`)
- **Sorting by time** — view a pet's tasks in chronological order regardless of entry order. (`Scheduler.sort_by_time`)
- **Filtering** — narrow tasks by pet name and/or completion status. (`Scheduler.filter_tasks`)
- **Conflict warnings** — non-blocking alerts when two tasks' preferred time windows overlap (same pet or across pets). (`Scheduler.detect_conflicts`)
- **Recurring tasks** — completing a `DAILY`/`WEEKLY` task automatically queues the next occurrence (`+1` / `+7` days); `ONCE` tasks don't repeat. (`Pet.complete_task`, `Task.next_occurrence`)
- **State persistence** — the `Owner` lives in `st.session_state`, so pets and tasks survive across UI interactions.

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

Run the full suite from the project root:

```bash
python -m pytest
```

**What the tests cover** (`tests/test_pawpal.py`, 13 tests split into happy paths and edge cases):

- **Task basics** — `mark_complete()` flips status; `add_task()` grows the pet's task list.
- **Sorting** — `sort_by_time()` returns tasks chronologically even when added out of order, and handles an empty list.
- **Filtering** — `filter_tasks()` narrows by pet name and by completion status.
- **Recurrence** — completing a `DAILY` task queues one due +1 day; a `WEEKLY` task +7 days; a `ONCE` task does not recur.
- **Conflict detection** — flags a same-pet overlap and an exact-same-time clash; reports nothing when time windows are disjoint.
- **Scheduling edge cases** — a pet with no tasks yields an empty plan; when time runs out, lower-priority tasks land in `unscheduled` instead of crashing.

Sample test output:

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.0.3, pluggy-1.6.0
collected 13 items

tests\test_pawpal.py .............                                       [100%]

============================= 13 passed in 0.11s ==============================
```

**Confidence level: ★★★★☆ (4/5).** The core behaviors — sorting, filtering, recurrence math, conflict detection, and the greedy scheduler's happy path and over-budget path — are all covered and green. Docking one star because a few areas aren't yet tested: recurrence across month/year boundaries, `preferred_start` times that fall outside the owner's waking window, and multi-day scheduling. See reflection section 4b for what I'd test next.

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time`, `Scheduler._sort_pairs` | Times are stored as integer minutes-from-midnight, so a single `sorted()` lambda key orders tasks — no `HH:MM` string parsing. The scheduler itself sorts by priority, then preferred time, then duration. |
| Filtering | `Scheduler.filter_tasks`, `Owner.all_tasks`, `Pet.pending_tasks` | Filter `(pet, task)` pairs by `pet_name` and/or `completed` status. |
| Conflict handling | `Scheduler.detect_conflicts` | Pairwise overlap check on preferred time windows; returns human-readable warnings (never raises), covering same-pet and cross-pet clashes. |
| Recurring tasks | `Task.next_occurrence`, `Pet.complete_task`, `Recurrence` enum | Completing a `DAILY`/`WEEKLY` task auto-queues the next instance, advancing `due_date` with `timedelta` (+1 or +7 days). `ONCE` tasks don't recur. |

## 📸 Demo Walkthrough

Launch the app with `streamlit run app.py`.

### What you can do in the UI

- **Owner & availability** — set the owner name, total available minutes for the day, and the waking window (day start/end).
- **Add a pet** — name, species, and optional breed. Duplicate names are rejected (the scheduler keys plans by pet name).
- **Manage tasks per pet** — pick a pet, then add tasks (title, duration, priority, optional preferred time). Each task has an expander to edit its fields, mark it complete, or delete it. A table shows the pet's tasks **sorted by time**.
- **Generate schedule** — builds a per-pet daily plan and shows any **conflict warnings** first.

### Example workflow

1. Set availability to, say, **120 minutes**, day **08:00–21:00**.
2. **Add a pet**: "Biscuit" (dog).
3. **Add tasks** for Biscuit: "Morning walk" (30 min, high, preferred 08:00, daily) and "Feeding" (10 min, high, preferred 08:00).
4. Watch the **sorted task table** update as you add tasks.
5. Click **Generate schedule**. Because both tasks want 08:00, a **conflict warning** appears; the plan then places Feeding at 08:00 and shifts Morning walk to the next open slot, with a `↳` reason on each line.
6. Tick **Completed** on the daily "Morning walk" — a toast confirms the **next occurrence** was queued for tomorrow.

### Key Scheduler behaviors shown

- **Sorting** by preferred time (`Scheduler.sort_by_time`) in the task table.
- **Conflict warnings** (`Scheduler.detect_conflicts`) surfaced via `st.warning` before the plan.
- **Priority packing + explanations** (`Scheduler.schedule` → `Plan.summary`).
- **Recurrence** (`Pet.complete_task`) when a daily/weekly task is completed.

### Sample CLI output (`python main.py`)

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

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
