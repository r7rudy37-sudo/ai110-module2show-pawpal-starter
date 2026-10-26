"""Streamlit front end for the PawPal+ backend."""
from datetime import date, datetime, time
import os
from pathlib import Path

import streamlit as st

from main import create_demo_owner
from pawpal_system import Owner, Pet, Scheduler, Task, clean_text, load_owner, save_owner

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
DATA_PATH = Path(os.environ.get("PAWPAL_DATA_PATH", "data/pawpal.json"))


def persist():
    """Save current data and show storage errors without hiding the problem."""
    try:
        save_owner(st.session_state.owner, DATA_PATH)
        return True
    except OSError as error:
        st.error(f"Your change is in this session, but could not be saved: {error}")
        return False


if "owner" not in st.session_state:
    try:
        st.session_state.owner = load_owner(DATA_PATH) if DATA_PATH.exists() else Owner("Pet owner")
    except (ValueError, OSError) as error:
        st.error(f"Could not load saved data: {error}")
        st.info("Your saved file was left unchanged. Repair it or choose a different PAWPAL_DATA_PATH.")
        st.stop()

owner = st.session_state.owner
scheduler = Scheduler(owner)
st.title("🐾 PawPal+")
st.caption("A little planning. Happier pets. Keep every pet's care in one place.")

with st.sidebar:
    st.header("Your household")
    with st.form("owner_form"):
        owner_name = st.text_input("Owner name", owner.name)
        if st.form_submit_button("Save owner"):
            try:
                owner.name = clean_text(owner_name, "Owner name")
                if persist():
                    st.success("Owner saved.")
            except ValueError as error:
                st.error(str(error))
    if not owner.pets and st.button("Load sample household"):
        st.session_state.owner = create_demo_owner(date.today())
        persist()
        st.rerun()
    st.caption("Changes save locally after each action. Use one browser session at a time.")
    st.divider()
    st.write("**How to use**")
    st.write("1. Add your pets.\n2. Schedule care tasks.\n3. Review warnings and build a daily plan.\n4. Mark tasks complete to create the next routine.")

first, second, third = st.columns(3)
first.metric("Pets", len(owner.pets))
second.metric("Pending tasks", len(scheduler.filter_tasks(completed=False)))
third.metric("Completed", len(scheduler.filter_tasks(completed=True)))

pets_tab, tasks_tab, plan_tab = st.tabs(["🐶 Pets", "📋 Care tasks", "🗓️ Daily plan"])
with pets_tab:
    st.subheader("Meet your pets")
    with st.form("pet_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        pet_name = col1.text_input("Pet name")
        species = col2.selectbox("Species", ["dog", "cat", "bird", "rabbit", "other"])
        if st.form_submit_button("Add pet", type="primary"):
            try:
                owner.add_pet(Pet(pet_name, species))
                if persist():
                    st.rerun()
            except ValueError as error:
                st.error(str(error))
    if owner.pets:
        st.table([{"Pet": pet.name, "Species": pet.species, "Care tasks": len(pet.tasks)} for pet in owner.pets])
    else:
        st.info("Add your first pet, or load the sample household in the sidebar.")

pet_ids = [pet.id for pet in owner.pets]


def pet_label(pet_id):
    """Distinguish pets that share a name."""
    pet = owner.get_pet(pet_id)
    return f"{pet.name} ({pet.species}, {pet.id[:6]})"


with tasks_tab:
    st.subheader("Schedule care")
    st.caption("Preferred time is a flexible start time. The daily plan explains any changes.")
    if not owner.pets:
        st.info("Add a pet first to schedule a task.")
    else:
        with st.form("task_form", clear_on_submit=True):
            selected_pet = st.selectbox("Pet", pet_ids, format_func=pet_label)
            description = st.text_input("Activity", placeholder="Morning walk, breakfast, medication...")
            a, b, c = st.columns(3)
            due_date = a.date_input("Date", date.today())
            due_time = b.time_input("Preferred time", time(8, 0))
            duration = c.number_input("Duration (minutes)", 1, 1440, 15)
            a, b = st.columns(2)
            priority = a.selectbox("Priority", ["high", "medium", "low"], index=1)
            frequency = b.selectbox("Repeat", ["none", "daily", "weekly"])
            if st.form_submit_button("Schedule task", type="primary"):
                try:
                    owner.get_pet(selected_pet).add_task(Task(description, datetime.combine(due_date, due_time), int(duration), priority, frequency))
                    if persist():
                        st.rerun()
                except ValueError as error:
                    st.error(str(error))
        st.divider()
        st.subheader("Your care tasks")
        a, b = st.columns(2)
        pet_filter = a.selectbox("Show pet", ["all"] + pet_ids, format_func=lambda value: "All pets" if value == "all" else pet_label(value))
        status = b.selectbox("Status", ["Pending", "Completed", "All"])
        filtered = scheduler.filter_tasks(None if pet_filter == "all" else pet_filter, {"Pending": False, "Completed": True, "All": None}[status])
        if not filtered:
            st.info("No tasks match these filters.")
        for task in scheduler.sort_by_time(filtered):
            with st.container(border=True):
                left, right = st.columns([5, 1])
                left.markdown(f"**{owner.get_pet(task.pet_id).name} · {task.description}**")
                left.caption(f"{task.due:%b %d, %Y · %H:%M} | {task.duration_minutes} min | {task.priority} priority | {task.frequency}")
                if task.completed:
                    right.success("Done")
                elif right.button("Complete", key=f"complete_{task.id}"):
                    scheduler.mark_task_complete(task.id)
                    if persist():
                        st.rerun()
                if not task.completed:
                    with st.expander("Edit task"):
                        with st.form(f"edit_{task.id}"):
                            edited_description = st.text_input("Activity", task.description)
                            e1, e2, e3 = st.columns(3)
                            edited_date = e1.date_input("Date", task.due.date())
                            edited_time = e2.time_input("Preferred time", task.due.time())
                            edited_duration = e3.number_input("Duration (minutes)", 1, 1440, task.duration_minutes)
                            e1, e2 = st.columns(2)
                            edited_priority = e1.selectbox("Priority", ["high", "medium", "low"], index=["high", "medium", "low"].index(task.priority))
                            edited_frequency = e2.selectbox("Repeat", ["none", "daily", "weekly"], index=["none", "daily", "weekly"].index(task.frequency))
                            if st.form_submit_button("Save changes"):
                                try:
                                    scheduler.update_task(task.id, description=edited_description, due=datetime.combine(edited_date, edited_time), duration_minutes=int(edited_duration), priority=edited_priority, frequency=edited_frequency)
                                    if persist():
                                        st.rerun()
                                except ValueError as error:
                                    st.error(str(error))

with plan_tab:
    st.subheader("One day, every pet")
    a, b, c = st.columns(3)
    selected_date = a.date_input("Plan date", date.today())
    start_time = b.time_input("Available from", time(8, 0))
    end_time = c.time_input("Available until", time(20, 0))
    pending = scheduler.filter_tasks(completed=False, on_date=selected_date)
    for warning in scheduler.detect_conflicts(selected_date):
        st.warning(warning)
    overdue = [task for task in scheduler.filter_tasks(completed=False) if task.due.date() < selected_date]
    if overdue:
        st.warning(f"{len(overdue)} earlier task(s) remain incomplete. Review them under Care tasks; they are not silently moved into this date.")
    if pending:
        st.table([{"Preferred": task.due.strftime("%H:%M"), "Pet": owner.get_pet(task.pet_id).name, "Activity": task.description, "Minutes": task.duration_minutes, "Priority": task.priority} for task in scheduler.sort_by_time(pending)])
    else:
        st.info("No pending tasks on this date.")
    st.caption("Plans reserve one owner's time. Higher priorities get the earliest free blocks at or after their preferred start. Review changes before following a plan.")
    if st.button("Generate schedule", type="primary"):
        try:
            plan = scheduler.build_plan(selected_date, datetime.combine(selected_date, start_time), datetime.combine(selected_date, end_time))
            if plan["scheduled"]:
                st.success(f"{len(plan['scheduled'])} task(s) fit without overlapping.")
                st.table([{"Start": block["start"].strftime("%H:%M"), "End": block["end"].strftime("%H:%M"), "Pet": owner.get_pet(block["task"].pet_id).name, "Activity": block["task"].description, "Priority": block["task"].priority} for block in plan["scheduled"]])
                st.markdown("**Why these times?**")
                for block in plan["scheduled"]:
                    st.caption(f"{block['task'].description}: {block['reason']}")
            else:
                st.info("No tasks fit this window.")
            for item in plan["skipped"]:
                st.warning(f"Deferred: {item['task'].description}. {item['reason']}")
        except ValueError as error:
            st.error(str(error))
