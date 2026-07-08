import datetime as dt

import streamlit as st

from pawpal_system import Owner, Pet, Task, Priority, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
**PawPal+** is a pet care planning assistant. Add your pets and their care tasks,
then generate a daily plan that orders everything by priority within the time you
have available — and explains why each task landed where it did.
"""
)

# --- helpers -----------------------------------------------------------------

PRIORITY_BY_LABEL = {
    "low": Priority.LOW,
    "medium": Priority.MEDIUM,
    "high": Priority.HIGH,
}
LABEL_BY_PRIORITY = {v: k for k, v in PRIORITY_BY_LABEL.items()}


def minutes_from_time(t: dt.time) -> int:
    """Convert a datetime.time into minutes-from-midnight."""
    return t.hour * 60 + t.minute


def time_from_minutes(minute: int) -> dt.time:
    """Convert minutes-from-midnight into a datetime.time."""
    minute = max(0, min(int(minute), 24 * 60 - 1))
    return dt.time(hour=minute // 60, minute=minute % 60)


# --- session state (the "vault") ---------------------------------------------
# st.session_state behaves like a dict. Create the Owner once and reuse it so the
# data persists across Streamlit reruns instead of being rebuilt every interaction.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
if "task_counter" not in st.session_state:
    st.session_state.task_counter = 0

owner: Owner = st.session_state.owner

st.divider()

# --- owner + daily constraints -----------------------------------------------
st.subheader("👤 Owner & daily availability")
owner.name = st.text_input("Owner name", value=owner.name)

c1, c2, c3 = st.columns(3)
with c1:
    owner.available_minutes = int(
        st.number_input(
            "Available minutes today",
            min_value=0,
            max_value=24 * 60,
            value=owner.available_minutes,
            step=15,
        )
    )
with c2:
    owner.day_start_minute = minutes_from_time(
        st.time_input("Day starts", value=time_from_minutes(owner.day_start_minute))
    )
with c3:
    owner.day_end_minute = minutes_from_time(
        st.time_input("Day ends", value=time_from_minutes(owner.day_end_minute))
    )

st.divider()

# --- add a pet ---------------------------------------------------------------
st.subheader("🐶 Add a pet")
with st.form("add_pet", clear_on_submit=True):
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        new_pet_name = st.text_input("Pet name", value="")
    with pc2:
        new_species = st.selectbox("Species", ["dog", "cat", "other"])
    with pc3:
        new_breed = st.text_input("Breed (optional)", value="")

    if st.form_submit_button("Add pet"):
        name = new_pet_name.strip()
        if not name:
            st.warning("Please enter a pet name.")
        elif any(p.name == name for p in owner.pets):
            # Scheduler keys plans by pet name, so names must be unique.
            st.warning(f"You already have a pet named '{name}'.")
        else:
            owner.add_pet(Pet(name=name, species=new_species, breed=new_breed.strip()))
            st.success(f"Added {name}.")
            st.rerun()

# --- per-pet task management -------------------------------------------------
if not owner.pets:
    st.info("No pets yet. Add one above to start planning tasks.")
else:
    st.divider()
    st.subheader("📋 Tasks")

    pet_names = [p.name for p in owner.pets]
    selected_name = st.selectbox("Choose a pet", pet_names)
    pet = next(p for p in owner.pets if p.name == selected_name)

    # Add a task to the selected pet.
    with st.form("add_task", clear_on_submit=True):
        st.markdown(f"**Add a task for {pet.name}**")
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            title = st.text_input("Task title", value="Morning walk")
        with tc2:
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20
            )
        with tc3:
            priority_label = st.selectbox("Priority", list(PRIORITY_BY_LABEL), index=2)

        set_pref = st.checkbox("Set a preferred start time")
        pref_time = st.time_input("Preferred start", value=dt.time(8, 0), disabled=not set_pref)

        if st.form_submit_button("Add task"):
            if not title.strip():
                st.warning("Please enter a task title.")
            else:
                st.session_state.task_counter += 1
                task = Task(
                    id=f"t{st.session_state.task_counter}",
                    title=title.strip(),
                    duration_minutes=int(duration),
                    priority=PRIORITY_BY_LABEL[priority_label],
                    preferred_start_minute=minutes_from_time(pref_time) if set_pref else None,
                )
                pet.add_task(task)
                st.success(f"Added '{task.title}' for {pet.name}.")
                st.rerun()

    # Existing tasks: edit / complete / delete.
    if not pet.tasks:
        st.caption(f"{pet.name} has no tasks yet.")
    else:
        st.markdown(f"**{pet.name}'s tasks**")
        for task in pet.tasks:
            done = " ✅" if task.completed else ""
            header = f"{task.title} — {task.duration_minutes} min [{LABEL_BY_PRIORITY[task.priority]}]{done}"
            with st.expander(header):
                completed = st.checkbox("Completed", value=task.completed, key=f"done_{task.id}")
                if completed != task.completed:
                    task.mark_complete(completed)
                    st.rerun()

                ec1, ec2 = st.columns(2)
                with ec1:
                    new_duration = st.number_input(
                        "Duration (minutes)",
                        min_value=1,
                        max_value=240,
                        value=task.duration_minutes,
                        key=f"dur_{task.id}",
                    )
                with ec2:
                    new_priority_label = st.selectbox(
                        "Priority",
                        list(PRIORITY_BY_LABEL),
                        index=list(PRIORITY_BY_LABEL).index(LABEL_BY_PRIORITY[task.priority]),
                        key=f"prio_{task.id}",
                    )

                set_pref_edit = st.checkbox(
                    "Preferred start time",
                    value=task.preferred_start_minute is not None,
                    key=f"setpref_{task.id}",
                )
                pref_edit = st.time_input(
                    "Preferred start",
                    value=time_from_minutes(task.preferred_start_minute or 8 * 60),
                    disabled=not set_pref_edit,
                    key=f"pref_{task.id}",
                )

                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("Save changes", key=f"save_{task.id}"):
                        pet.edit_task(
                            task.id,
                            duration_minutes=int(new_duration),
                            priority=PRIORITY_BY_LABEL[new_priority_label],
                            preferred_start_minute=(
                                minutes_from_time(pref_edit) if set_pref_edit else None
                            ),
                        )
                        st.success("Saved.")
                        st.rerun()
                with bc2:
                    if st.button("🗑 Delete", key=f"del_{task.id}"):
                        pet.remove_task(task.id)
                        st.rerun()

st.divider()

# --- generate the schedule ---------------------------------------------------
st.subheader("🗓 Today's Schedule")
if st.button("Generate schedule", type="primary"):
    if not owner.all_tasks():
        st.info("No pending tasks to schedule. Add some tasks (and leave them uncompleted).")
    else:
        plans = Scheduler().schedule(owner)
        for plan in plans.values():
            st.markdown(f"#### {plan.pet.name} ({plan.pet.species})")
            st.code(plan.summary(), language="text")
