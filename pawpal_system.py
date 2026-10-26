"""UI-independent pet care models and deterministic scheduling algorithms.

Times are naive local wall-clock datetimes. A task's due value is its preferred
start time; the generated plan may move it later and explains that change.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

PRIORITIES = {"high": 0, "medium": 1, "low": 2}
FREQUENCIES = {"none": 0, "daily": 1, "weekly": 7}


def clean_text(value: str, label: str) -> str:
    """Reject empty text and return trimmed user input."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} cannot be empty.")
    return value.strip()


@dataclass
class Task:
    """One occurrence of a care activity, with a stable identifier."""
    description: str
    due: datetime
    duration_minutes: int = 15
    priority: str = "medium"
    frequency: str = "none"
    completed: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)
    pet_id: str = ""

    def __post_init__(self):
        self.description = clean_text(self.description, "Task description")
        if not isinstance(self.due, datetime) or self.due.tzinfo is not None:
            raise ValueError("Due time must be a local datetime without a timezone.")
        if type(self.duration_minutes) is not int or not 1 <= self.duration_minutes <= 1440:
            raise ValueError("Duration must be a whole number from 1 to 1440 minutes.")
        if self.priority not in PRIORITIES:
            raise ValueError("Choose high, medium, or low priority.")
        if self.frequency not in FREQUENCIES:
            raise ValueError("Choose none, daily, or weekly recurrence.")
        if type(self.completed) is not bool:
            raise ValueError("Completion status must be true or false.")
        self.id = clean_text(self.id, "Task ID")
        if not isinstance(self.pet_id, str):
            raise ValueError("Pet ID must be text.")

    def mark_complete(self) -> bool:
        """Complete this occurrence; return False if it was already complete."""
        if self.completed:
            return False
        self.completed = True
        return True


@dataclass
class Pet:
    """A pet and its collection of care tasks."""
    name: str
    species: str
    tasks: List[Task] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self):
        self.name = clean_text(self.name, "Pet name")
        self.species = clean_text(self.species, "Species")
        self.id = clean_text(self.id, "Pet ID")
        original = self.tasks
        self.tasks = []
        for task in original:
            self.add_task(task)

    def add_task(self, task: Task) -> None:
        """Attach a task once and prevent moving it to another pet by accident."""
        if task.pet_id and task.pet_id != self.id:
            raise ValueError("This task belongs to another pet.")
        if any(existing.id == task.id for existing in self.tasks):
            raise ValueError("This task is already attached to this pet.")
        task.pet_id = self.id
        self.tasks.append(task)

    def list_tasks(self) -> List[Task]:
        """Return a copy of this pet's task list."""
        return list(self.tasks)


@dataclass
class Owner:
    """One owner's pets and the common access point used by the scheduler."""
    name: str
    pets: List[Pet] = field(default_factory=list)

    def __post_init__(self):
        self.name = clean_text(self.name, "Owner name")
        original = self.pets
        self.pets = []
        for pet in original:
            self.add_pet(pet)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with a unique identifier."""
        if any(existing.id == pet.id for existing in self.pets):
            raise ValueError("This pet is already registered.")
        existing_ids = {task.id for task in self.get_all_tasks()}
        if any(task.id in existing_ids for task in pet.tasks):
            raise ValueError("Task IDs must be unique across pets.")
        self.pets.append(pet)

    def get_pet(self, pet_id: str) -> Pet:
        """Find a pet by ID, including when two pets have the same name."""
        for pet in self.pets:
            if pet.id == pet_id:
                return pet
        raise ValueError("Pet was not found.")

    def get_all_tasks(self) -> List[Task]:
        """Collect every pet's tasks; do not expose just the first pet."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:
    """Organize all pets' care using an Owner's task collection."""

    def __init__(self, owner: Owner):
        self.owner = owner

    def filter_tasks(self, pet_id: Optional[str] = None,
                     completed: Optional[bool] = None,
                     on_date: Optional[date] = None) -> List[Task]:
        """Filter by stable pet ID, completion state, and preferred date."""
        return [task for task in self.owner.get_all_tasks()
                if (pet_id is None or task.pet_id == pet_id)
                and (completed is None or task.completed == completed)
                and (on_date is None or task.due.date() == on_date)]

    def sort_by_time(self, tasks: Optional[List[Task]] = None) -> List[Task]:
        """Return a stable chronological copy; keep the original list unchanged."""
        source = self.owner.get_all_tasks() if tasks is None else tasks
        return sorted(source, key=lambda task: task.due)

    def sort_by_priority(self, tasks: Optional[List[Task]] = None) -> List[Task]:
        """Rank high before medium before low, breaking ties by preferred time."""
        source = self.owner.get_all_tasks() if tasks is None else tasks
        return sorted(source, key=lambda task: (PRIORITIES[task.priority], task.due))

    def detect_conflicts(self, on_date: Optional[date] = None) -> List[str]:
        """Warn about overlapping pending tasks across all pets.

        Intervals are half-open: a task ending at 09:00 does not conflict with
        one beginning at 09:00. Completed occurrences do not cause warnings.
        """
        tasks = self.sort_by_time(self.filter_tasks(completed=False))
        warnings = []
        for index, first in enumerate(tasks):
            end = first.due + timedelta(minutes=first.duration_minutes)
            for second in tasks[index + 1:]:
                if second.due >= end:
                    break
                if on_date is not None:
                    day_start = datetime.combine(on_date, datetime.min.time())
                    day_end = day_start + timedelta(days=1)
                    overlap_start = max(first.due, second.due, day_start)
                    overlap_end = min(end, second.due + timedelta(
                        minutes=second.duration_minutes), day_end)
                    if overlap_start >= overlap_end:
                        continue
                first_pet = self.owner.get_pet(first.pet_id).name
                second_pet = self.owner.get_pet(second.pet_id).name
                warnings.append(
                    f"{first.due:%Y-%m-%d %H:%M} {first_pet}: {first.description} "
                    f"overlaps {second.due:%H:%M} {second_pet}: {second.description}.")
        return warnings

    def mark_task_complete(self, task_id: str) -> Optional[Task]:
        """Complete once and append one new daily/weekly occurrence.

        Recurrence advances from the scheduled date, preserving the routine
        even when completion is late. Repeated clicks cannot duplicate it.
        """
        for task in self.owner.get_all_tasks():
            if task.id != task_id:
                continue
            days = FREQUENCIES[task.frequency]
            # Validate the next occurrence before changing existing state.
            next_task = (replace(task, due=task.due + timedelta(days=days),
                                 completed=False, id=uuid4().hex)
                         if days and not task.completed else None)
            if not task.mark_complete():
                return None
            if next_task is not None:
                self.owner.get_pet(task.pet_id).add_task(next_task)
            return next_task
        raise ValueError("Task was not found.")

    def update_task(self, task_id: str, **changes) -> Task:
        """Validate an edited pending task before replacing it in its pet."""
        allowed = {"description", "due", "duration_minutes", "priority", "frequency"}
        if not set(changes).issubset(allowed):
            raise ValueError("Only description, time, duration, priority, and frequency can be edited.")
        for pet in self.owner.pets:
            for index, task in enumerate(pet.tasks):
                if task.id == task_id:
                    if task.completed:
                        raise ValueError("Completed occurrences cannot be edited.")
                    updated = replace(task, **changes)
                    pet.tasks[index] = updated
                    return updated
        raise ValueError("Task was not found.")

    def build_plan(self, on_date: date, start: datetime, end: datetime) -> dict:
        """Allocate non-overlapping blocks within one availability window.

        This greedy algorithm places higher priorities first at the earliest
        free slot on/after their preferred start. It never changes stored tasks
        or silently drops tasks that do not fit. It does not optimize globally.
        """
        if start.tzinfo is not None or end.tzinfo is not None:
            raise ValueError("Use local times without timezone offsets.")
        if start >= end or start.date() != on_date or end.date() != on_date:
            raise ValueError("Choose an end after the start on the selected date.")
        scheduled, skipped = [], []
        tasks = self.sort_by_priority(self.filter_tasks(completed=False, on_date=on_date))
        for task in tasks:
            candidate = max(start, task.due)
            duration = timedelta(minutes=task.duration_minutes)
            for block in sorted(scheduled, key=lambda item: item["start"]):
                if candidate + duration <= block["start"]:
                    break
                if candidate < block["end"]:
                    candidate = block["end"]
            if candidate + duration > end:
                skipped.append({"task": task, "reason": "No free block fits before availability ends."})
                continue
            reason = f"{task.priority.title()} priority; earliest free block at/after preferred time."
            if candidate != task.due:
                reason += f" Moved from {task.due:%H:%M} to avoid a conflict or fit availability."
            scheduled.append({"task": task, "start": candidate,
                              "end": candidate + duration, "reason": reason})
        scheduled.sort(key=lambda item: item["start"])
        return {"scheduled": scheduled, "skipped": skipped}


def save_owner(owner: Owner, path) -> None:
    """Atomically save owner data as JSON, outside tracked project files."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps({"version": 1, "owner": asdict(owner)},
                                   default=lambda value: value.isoformat(), indent=2),
                         encoding="utf-8")
    temporary.replace(destination)


def load_owner(path) -> Owner:
    """Validate a JSON save and rebuild real Owner/Pet/Task instances."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data["version"] != 1:
            raise ValueError("Unsupported save version.")
        raw_owner = data["owner"]
        owner = Owner(raw_owner["name"])
        for raw_pet in raw_owner["pets"]:
            pet = Pet(raw_pet["name"], raw_pet["species"], id=raw_pet["id"])
            for raw_task in raw_pet["tasks"]:
                task_data = dict(raw_task)
                task_data["due"] = datetime.fromisoformat(task_data["due"])
                pet.add_task(Task(**task_data))
            owner.add_pet(pet)
        return owner
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ValueError(f"Invalid PawPal save: {error}") from error
