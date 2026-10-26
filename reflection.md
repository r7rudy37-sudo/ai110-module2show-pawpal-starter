# 🐾 PawPal+

PawPal+ is a local pet care planner built for the CodePath AI110 PawPal+ project. Add multiple pets, schedule care tasks, review conflicts, and generate a daily plan within your available time. The same Python backend powers a reproducible terminal demo and a working Streamlit interface.

## Features

- Owner information and multiple pets, with stable IDs so matching names stay separate.
- Add and edit tasks with a preferred date/time, duration, priority, and recurrence.
- Sort chronologically and filter by pet, completion state, and date.
- Show exact-time and duration-overlap warnings across every pet.
- Complete an occurrence once; daily and weekly tasks automatically receive one successor.
- Build a priority-based plan with non-overlapping blocks and explanations for moved or deferred tasks.
- Keep data across Streamlit reruns and application restarts with validated JSON save/load.
- Display household counts, task cards, readable tables, helpful empty states, warnings, and success messages.

## Setup and run

Use Python 3.9 or later. The verified environment used Python 3.9.6, Streamlit 1.50.0, and pytest 8.4.2.

```bash
git clone https://github.com/r7rudy37-sudo/ai110-module2show-pawpal-starter.git
cd ai110-module2show-pawpal-starter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
python -m streamlit run app.py
```

On Windows PowerShell, create the environment with `python -m venv .venv` and activate it with `.venv\Scripts\Activate.ps1`. Open the local address printed by Streamlit.

## Implementation summary

| Class | Responsibility |
|---|---|
| `Task` | A validated care occurrence: description, preferred datetime, duration, priority, frequency, completion state, task ID, and pet ID. `mark_complete()` changes status once. |
| `Pet` | Pet identity and its tasks; `add_task()` and `list_tasks()` manage the collection. |
| `Owner` | Owner name and pets; `add_pet()`, `get_pet()`, and `get_all_tasks()` provide access. |
| `Scheduler` | Reads `Owner.get_all_tasks()` to sort, filter, detect conflicts, complete recurring tasks, edit pending tasks, and build plans across multiple pets. |

`pawpal_system.py` contains the backend and JSON helpers. `main.py` is the deterministic CLI demo. `app.py` imports the backend and keeps the owner in `st.session_state`; its forms call real methods rather than keeping a separate list of UI dictionaries.

The draft architecture is in [diagrams/uml_draft.mmd](diagrams/uml_draft.mmd). The final source is in [diagrams/uml_final.mmd](diagrams/uml_final.mmd), also copied to [diagrams/uml.mmd](diagrams/uml.mmd) for starter-repository compatibility.

## Smarter Scheduling

| Feature | Method | Behavior |
|---|---|---|
| Chronological sorting | `Scheduler.sort_by_time()` | Stable sorting by full datetime without changing stored task order. An explicitly empty list stays empty. |
| Priority sorting | `Scheduler.sort_by_priority()` | High, medium, low; ties use preferred time. |
| Filtering | `Scheduler.filter_tasks()` | Combine pet ID, completion state, and preferred date; includes all pets by default. |
| Conflict detection | `Scheduler.detect_conflicts()` | Compare pending duration intervals across pets and midnight. Adjacent tasks are allowed. Return warnings rather than crash. |
| Recurrence | `Scheduler.mark_task_complete()` | Mark an occurrence complete and attach one new task to the same pet, one or seven days after its scheduled date. Repeated completion does not duplicate it. |
| Validated edits | `Scheduler.update_task()` | Replace a pending task only after all edited fields validate. |
| Priority time-blocking | `Scheduler.build_plan()` | Place higher priorities first in the earliest free block on/after their preferred time, inside the selected same-day availability window. Explain moved tasks and return tasks that do not fit. |

Sorting costs O(n log n). Conflict detection and greedy placement can take O(n²) in the worst case, which is reasonable for a small household. The planner fills gaps when a task fits; it does not search for a globally optimal arrangement.

## Demo Walkthrough

1. Run `python -m streamlit run app.py`. Save an owner name in the sidebar.
2. Under **Pets**, add Mochi the dog and Luna the cat. On an empty household, **Load sample household** provides a ready-to-run example for the current day.
3. Under **Care tasks**, add a 30-minute high priority walk for Mochi at 08:00 and a 10-minute high priority breakfast for Luna at 08:00. Set both to repeat daily. Task cards show the pet, date, time, duration, priority, and repeat rule. **Edit task** changes pending tasks.
4. Under **Daily plan**, choose the date and availability. The warning identifies the two overlapping activities. **Generate schedule** reserves 08:00–08:30 for the walk and 08:30–08:40 for breakfast, explaining the change. With an 08:00–10:00 window, the sample household's evening walk is listed as deferred.
5. Return to **Care tasks**, filter by pet/status, and click **Complete**. The original occurrence is kept in completed history and one new occurrence appears on the following date. Save/load retains this state across restarts.

`main.py` uses a fixed October 26, 2026 date so its output is reproducible on any day. The browser's sample household uses the current local date instead.

## Sample Output

Captured from `python main.py`:

```text
PAWPAL+ | Today's Schedule | 2026-10-26
TIME   PET      ACTIVITY           MIN  PRIORITY  REPEAT
08:00  Mochi    Morning walk        30  high      daily
08:00  Luna     Breakfast           10  high      daily
09:00  Luna     Grooming            20  low       weekly
18:00  Mochi    Evening walk        30  medium    daily

Conflict warnings:
! 2026-10-26 08:00 Mochi: Morning walk overlaps 08:00 Luna: Breakfast.

Pending tasks for Luna:
- Breakfast
- Grooming

Priority plan | available 08:00-10:00:
08:00-08:30 | Mochi: Morning walk
  High priority; earliest free block at/after preferred time.
08:30-08:40 | Luna: Breakfast
  High priority; earliest free block at/after preferred time. Moved from 08:00 to avoid a conflict or fit availability.
09:00-09:20 | Luna: Grooming
  Low priority; earliest free block at/after preferred time.
Deferred: Evening walk. No free block fits before availability ends.

Completed: Breakfast. Next occurrence: 2026-10-27 08:00.
Repeated completion creates no duplicate: 5 total occurrences.
```

## Testing PawPal+

```bash
python -m pytest
# Concise output used below:
python -m pytest -q
```

The suite covers multi-pet collection and sorting, filtering, daily/weekly recurrence, completion idempotence, missing tasks, partial and exact overlaps, midnight and year boundaries, adjacent intervals, priority placement, gap filling, exact availability limits, empty schedules, invalid input, edits, equal pet names, save/load, and malformed JSON. Two Streamlit tests operate real forms through add, edit, completion, rerun, planning, and restart workflows, using temporary save files.

Actual passing test output:

```text
..........................                                               [100%]
26 passed in 1.05s
```

**Technical confidence: 4/5**, based on the passing automated suite and a live browser check of the populated household, overlap warning, and generated four-task plan. This rating describes the implemented prototype's scope.

## Data persistence

`save_owner()` writes JSON to a temporary file and replaces the destination after a successful write. `load_owner()` reconstructs validated `Owner`, `Pet`, and `Task` instances. `app.py` automatically saves each successful action to `data/pawpal.json` and loads it at startup. A malformed file produces an error and is left unchanged. Storage errors remain visible instead of reporting a successful save.

For a separate data file, set `PAWPAL_DATA_PATH` before starting Streamlit. The default path is relative to the directory from which you launch the app. The `data/` folder and virtual environment are ignored by Git. The CLI demo does not read or write household data. Persistence changes are in `pawpal_system.py` and `app.py`; round-trip checks are in `tests/test_pawpal.py` and `tests/test_app.py`.

## UI and output formatting

`main.main()` prints aligned columns and explicit sections for warnings, filtering, plans, deferred tasks, and recurrence. `app.py` uses Streamlit tabs, `st.metric`, bordered task cards, `st.table`, `st.caption`, `st.success`, `st.warning`, and form validation. Plan explanations appear below the compact schedule so a long explanation does not squeeze the time columns.

## Scope and limitations

- One local owner, one availability window per day, and one browser session at a time. JSON is not a multi-user database.
- Times are local wall-clock datetimes without timezone conversion or daylight-saving handling.
- Preferred times can move later; they are not medical deadlines. The planner does not change original task times.
- Tasks from earlier dates remain visible for review. Late completion advances recurrence from the scheduled date and can produce an overdue occurrence.
- The greedy plan prioritizes higher importance; it does not guarantee the maximum number of tasks or an optimal overall schedule.
- No reminders, authentication, external AI API calls, or automatic medication decisions are included.

## AI collaboration

This project was generated with Codex in response to the student's completion request. [reflection.md](reflection.md) and [ai_interactions.md](ai_interactions.md) honestly document the build, decisions, test correction, and limitations. The reflection does not invent personal student experiences or claim separate chat/model comparisons. The student should review the code, verify the behavior, and add their own learning observations.

Starter: [CodePath PawPal+](https://github.com/codepath/ai110-module2show-pawpal-starter).
