# AI Interactions Log

## Attribution and scope
Tool: Codex desktop. One continuous AI-assisted session on October 26, 2026. No comparison between different AI models was performed. This log records agent work and design review; it does not invent student prompts or manual verification.

Actual student request: "do this project until complete finish this project until complete", with the CodePath AI110 Unit 5 link.

## Agent Workflow

The requested task was to complete PawPal+. The agent read the live course instructions, grading rubric, and starter repository; forked the starter; created a draft design; implemented and ran the CLI before replacing the interface; added scheduling and persistence; tested the backend and interface; and wrote documentation.

Files modified or added:

- `pawpal_system.py`: four dataclasses/classes, sorting/filtering, interval conflicts, idempotent recurrence, validated editing, priority time-blocking, and JSON persistence.
- `main.py`: reproducible two-pet CLI example with sorting, conflicts, filtering, a constrained plan, and recurrence.
- `app.py`: actual backend calls, session state, forms, editing, completion, warnings, tables, and save/load.
- `tests/test_pawpal.py`, `tests/test_app.py`: backend behavior and Streamlit workflow tests.
- `diagrams/uml_draft.mmd`, `diagrams/uml_final.mmd`, `diagrams/uml.mmd`: initial and final architecture.
- `README.md`, `reflection.md`, `.gitignore`, and `evidence/`: documentation, limitations, and captured verification output.

The agent completed the implementation and ran automated checks and browser verification. Student review is still needed before treating the reflection as a personal account. No separate student testing or manual code correction is claimed.

## Design alternatives reviewed

These are design questions addressed by the agent during this build, not a fabricated transcript of student prompts or separate model responses.

| Question | Simple option | Chosen option and reason |
|---|---|---|
| How should tasks be ordered? | Sort `HH:MM` strings as suggested by the instructions. | Use a full datetime so tasks on different dates and recurring occurrences sort correctly. |
| What counts as a conflict? | Equal start times only. | Compare half-open duration intervals, including across pets and midnight; adjacent intervals remain allowed. |
| Where should recurrence live? | Generate a task every time the completion button is clicked. | Scheduler completes an occurrence only once and then attaches one successor to the same pet. |
| How should availability work? | Show a sorted list even if everything cannot fit. | Rank by priority and find free blocks; return explicit deferred items without changing original preferred times. |

## Verification and corrections

Initial full run: 25 checks passed; one UI check reached the default three-second AppTest timeout. The agent changed the AppTest timeout to 15 seconds, then ran both UI tests successfully and reran the full suite. The final suite has 26 passing checks. Tests use temporary paths and do not overwrite the live household.

The planner's scope is intentionally limited: one owner's time, a single same-day availability window, flexible preferred start times, and a greedy placement strategy. It does not guarantee a globally optimal plan or handle medical deadlines.

## Prompt comparison

No two-model or separate-prompt experiment was conducted. The design-alternatives table above is a review of approaches within one agent workflow. No unsupported bonus claim is made for the rubric's model/prompt comparison category.
