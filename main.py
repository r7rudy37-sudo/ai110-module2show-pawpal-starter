"""Reproducible terminal demonstration; no user data is read or written."""
from datetime import date, datetime
from pawpal_system import Owner, Pet, Scheduler, Task


def create_demo_owner(on_date=None):
    """Build a two-pet example with intentionally unsorted, overlapping tasks."""
    day = on_date or date(2026, 10, 26)
    owner = Owner("Jordan")
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(Task("Evening walk", datetime.combine(day, datetime.strptime("18:00", "%H:%M").time()), 30, "medium", "daily"))
    mochi.add_task(Task("Morning walk", datetime.combine(day, datetime.strptime("08:00", "%H:%M").time()), 30, "high", "daily"))
    luna.add_task(Task("Breakfast", datetime.combine(day, datetime.strptime("08:00", "%H:%M").time()), 10, "high", "daily"))
    luna.add_task(Task("Grooming", datetime.combine(day, datetime.strptime("09:00", "%H:%M").time()), 20, "low", "weekly"))
    return owner


def main():
    """Demonstrate sorting, filtering, conflicts, time-blocking, and recurrence."""
    owner = create_demo_owner()
    scheduler = Scheduler(owner)
    print("PAWPAL+ | Today's Schedule | 2026-10-26")
    print("TIME   PET      ACTIVITY           MIN  PRIORITY  REPEAT")
    for task in scheduler.sort_by_time():
        pet = owner.get_pet(task.pet_id)
        print(f"{task.due:%H:%M}  {pet.name:<7}  {task.description:<17}  {task.duration_minutes:>3}  {task.priority:<8}  {task.frequency}")
    print("\nConflict warnings:")
    for warning in scheduler.detect_conflicts():
        print(f"! {warning}")
    print("\nPending tasks for Luna:")
    for task in scheduler.filter_tasks(pet_id=owner.pets[1].id, completed=False):
        print(f"- {task.description}")
    print("\nPriority plan | available 08:00-10:00:")
    plan = scheduler.build_plan(date(2026, 10, 26), datetime(2026, 10, 26, 8), datetime(2026, 10, 26, 10))
    for block in plan["scheduled"]:
        task = block["task"]
        print(f"{block['start']:%H:%M}-{block['end']:%H:%M} | {owner.get_pet(task.pet_id).name}: {task.description}")
        print(f"  {block['reason']}")
    for item in plan["skipped"]:
        print(f"Deferred: {item['task'].description}. {item['reason']}")
    breakfast = owner.pets[1].tasks[0]
    next_task = scheduler.mark_task_complete(breakfast.id)
    print(f"\nCompleted: {breakfast.description}. Next occurrence: {next_task.due:%Y-%m-%d %H:%M}.")
    scheduler.mark_task_complete(breakfast.id)
    print(f"Repeated completion creates no duplicate: {len(owner.get_all_tasks())} total occurrences.")


if __name__ == "__main__":
    main()
