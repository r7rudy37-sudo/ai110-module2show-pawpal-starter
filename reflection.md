# PawPal+ Project Reflection

**Process note:** This is a factual reflection on the AI-assisted build in Codex. The student requested completion of the project; Codex generated the implementation, tests, documentation, and this process record. It does not claim that the student personally wrote the code, ran the checks, rejected a suggestion, or used separate chat sessions. Personal learning observations should be added by the student after reviewing the app.

## 1. System Design

### a. Initial design
The three main user actions are adding a pet, scheduling a care task, and viewing a daily plan. The initial design used four classes. `Task` held the activity, preferred datetime, repeat frequency, and completion state. `Pet` held identifying information and its tasks. `Owner` held multiple pets and collected all their tasks. `Scheduler` read from `Owner.get_all_tasks()` and put the tasks in time order. The initial implementation and diagram are preserved in the first project commit and `diagrams/uml_draft.mmd`.

### b. Design changes
The final design adds stable IDs, durations, priorities, validated editing, conflict detection, recurrence, and planning. IDs let two pets share a name without mixing up their tasks. Recurrence is managed by `Scheduler.mark_task_complete()` so the next task is attached to the correct pet. `Task.mark_complete()` only changes that occurrence's status. JSON save/load functions stay outside the UI and rebuild real dataclass instances. The final Mermaid source matches these responsibilities.

## 2. Scheduling Logic and Tradeoffs

### a. Constraints and priorities
The schedule uses the selected date, the owner's availability, task duration, completion state, preferred start time, and priority. High priority tasks get free blocks before medium and low priority tasks. Within a priority, the earlier preferred time comes first. All pets share one owner's time. The result explains moved tasks and lists tasks that do not fit.

### b. Tradeoffs
The planner uses a readable greedy algorithm instead of searching every possible arrangement. This is easy to explain and test for a small household, but it may not fit the largest possible number of tasks. Preferred start times are flexible, not medical deadlines. Tasks cannot start earlier than their preferred time. An incomplete task from an earlier date is flagged for review instead of silently being moved. Repeated tasks advance from the original scheduled date, so late completion preserves the routine and can create another overdue occurrence. This is documented rather than hidden.

## 3. AI Collaboration

### a. How AI was used
Codex read the project requirements and rubric, created a four-class design, edited several files, ran the demo, and generated behavioral tests. The agent workflow was useful because backend, interface, and tests needed consistent method names. The most useful strategy was turning requirements into specific observable checks, such as completing a daily task twice and verifying that only one next occurrence exists.

This build used one continuous Codex chat. It did not follow the suggested separate-chat workflow. Files and meaningful commits separated the phases instead. Separate chats could help limit context in a future student-led build, but that benefit was not tested here.

### b. Judgment and verification
A simple approach suggested in the course material is sorting `HH:MM` strings. The implementation instead uses full datetimes because recurring tasks need real dates and month/year rollover must be correct. Another reviewed alternative was exact-time-only conflict detection. The final code compares duration intervals, which also catches an 08:00 walk overlapping an 08:20 medication task. This was an agent design decision, not a claimed student rejection.

The first full test run passed 25 checks and hit Streamlit's default three-second test timeout on an early app rerun. The UI test budget was increased to 15 seconds, and the interface tests then passed in about one second. The full suite was rerun successfully. No scheduling assertion was weakened to make tests pass.

## 4. Testing and Verification

### a. What was tested
The tests verify sorting across two pets without mutating source order; filtering by pet, date, and status; daily and weekly recurrence across a year boundary; duplicate completion; missing task IDs; exact-time and partial overlaps; completed-task exclusion; midnight boundaries; priority-based time blocks; gap filling; exact end times; invalid inputs; validated edits; equal pet names; JSON round trips; and malformed saves. Streamlit tests exercise actual owner, pet, and task forms, editing, completion, reruns, persistence, conflict warnings, and generated plans.

### b. Confidence
The evidence supports a **4/5 technical confidence rating**, assigned by the agent for the implemented scope. All 26 tests pass. This is not a student self-rating. More testing would be useful for several browser sessions writing at once, very large schedules, daylight-saving transitions, and damaged files during a disk failure. The app is a local single-owner prototype using local wall-clock times.

## 5. Reflection

### a. What went well
The same backend drives the terminal demo and Streamlit interface. This makes it possible to verify the core behavior without relying only on what the page looks like. The demonstration shows multi-pet sorting, a warning, a revised plan, a deferred task, and recurrence.

### b. What could improve
A future version could support multiple caregivers, deadline-aware scheduling, configurable missed-task handling, timezones, database transactions, and reminders. Medication timing would need dedicated rules rather than flexible preferred times.

### c. Key takeaway
The engineering lesson illustrated by this build is that AI-generated code needs explicit constraints and independent checks. The human lead architect still needs to review the behavior, understand tradeoffs, and decide whether the result fits the real use case. The student's personal takeaway has not been supplied and is not invented here.
