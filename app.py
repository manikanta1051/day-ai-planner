"""
Day AI Planner - Main Streamlit Application

Purpose:
    Provide the browser interface for creating, saving,
    viewing, editing, downloading, and deleting daily plans.

Main features:
    1. Display an empty new-plan form.
    2. Show light placeholder examples.
    3. Generate plans using Groq.
    4. Save plans in SQLite.
    5. View saved-plan history.
    6. Edit and normalize schedule times.
    7. Download JSON and CSV files.
    8. Delete saved plans.
"""

import json
from datetime import time
from typing import Any

import streamlit as st

# Import SQLite database functions.
from database.database_service import (
    delete_plan,
    get_plan_by_id,
    get_plan_history,
    save_plan,
    update_plan,
)

# Import Groq planning functions.
from services.planner_service import (
    generate_daily_plan,
    get_model_name,
)

# Import JSON and CSV export functions.
from utils.exporters import (
    plan_to_csv,
    plan_to_json,
)

# Import flexible time normalization.
from utils.time_utils import (
    normalize_edited_schedule,
)

# Import form and plan validation.
from utils.validators import (
    validate_plan,
    validate_user_inputs,
)


# --------------------------------------------------
# Streamlit page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Day AI Planner",
    page_icon="📅",
    layout="wide",
)


# --------------------------------------------------
# Function: Format a selected form time
# --------------------------------------------------

def format_time(
    value: time,
) -> str:
    """
    Convert a Python time object into h:mm AM/PM text.

    Parameters:
        value:
            Time selected using st.time_input.

    Returns:
        str:
            Formatted time text.

    Examples:
        08:00 becomes 8:00 AM.
        18:30 becomes 6:30 PM.
    """

    return value.strftime(
        "%I:%M %p"
    ).lstrip("0")


# --------------------------------------------------
# Function: Get editor version
# --------------------------------------------------

def get_editor_version(
    plan_id: int,
) -> int:
    """
    Return the current version of a saved-plan editor.

    Streamlit widgets preserve values when their keys
    remain the same. The editor version is increased
    after a saved plan is updated so that normalized
    database values appear in fresh widgets.

    Parameters:
        plan_id:
            Database ID of the selected plan.

    Returns:
        int:
            Current editor version.
    """

    state_key = (
        f"edit_form_version_{plan_id}"
    )

    if state_key not in st.session_state:
        st.session_state[state_key] = 0

    return int(
        st.session_state[state_key]
    )


# --------------------------------------------------
# Function: Refresh editor after update
# --------------------------------------------------

def advance_editor_version(
    plan_id: int,
) -> None:
    """
    Increase a saved-plan editor's version.

    Parameters:
        plan_id:
            Database ID of the updated plan.

    Returns:
        None
    """

    state_key = (
        f"edit_form_version_{plan_id}"
    )

    current_version = int(
        st.session_state.get(
            state_key,
            0,
        )
    )

    st.session_state[
        state_key
    ] = current_version + 1


# --------------------------------------------------
# Function: Display one plan
# --------------------------------------------------

def display_daily_plan(
    daily_plan: dict[str, Any],
    download_prefix: str,
    show_metadata: bool = False,
) -> None:
    """
    Display a generated or saved daily plan.

    The function displays:
        - Plan metadata
        - Summary
        - Schedule table
        - Warnings
        - Raw JSON
        - JSON download
        - CSV download

    Parameters:
        daily_plan:
            Complete daily-plan dictionary.

        download_prefix:
            Prefix used for downloaded filenames
            and Streamlit widget keys.

        show_metadata:
            Display database metadata when True.

    Returns:
        None
    """

    # ----------------------------------------------
    # Display saved-plan metadata
    # ----------------------------------------------

    if show_metadata:

        (
            id_column,
            date_column,
            model_column,
        ) = st.columns(3)

        with id_column:
            st.metric(
                label="Plan ID",
                value=daily_plan.get(
                    "id",
                    "Unknown",
                ),
            )

        with date_column:
            st.metric(
                label="Created at",
                value=daily_plan.get(
                    "created_at",
                    "Unknown",
                ),
            )

        with model_column:
            st.metric(
                label="Model",
                value=daily_plan.get(
                    "model_name",
                    "Unknown",
                ),
            )

    # ----------------------------------------------
    # Display summary
    # ----------------------------------------------

    st.subheader("Plan summary")

    st.write(
        daily_plan["summary"]
    )

    # ----------------------------------------------
    # Display schedule
    # ----------------------------------------------

    st.subheader("Schedule")

    st.dataframe(
        daily_plan["schedule"],
        use_container_width=True,
        hide_index=True,
    )

    # ----------------------------------------------
    # Display warnings
    # ----------------------------------------------

    warnings = daily_plan.get(
        "warnings",
        [],
    )

    if warnings:

        st.subheader("Warnings")

        for warning in warnings:
            st.warning(warning)

    # ----------------------------------------------
    # Display raw JSON
    # ----------------------------------------------

    with st.expander(
        "View raw JSON response"
    ):
        st.json(daily_plan)

    # ----------------------------------------------
    # Prepare downloadable data
    # ----------------------------------------------

    json_download_data = plan_to_json(
        daily_plan
    )

    csv_download_data = plan_to_csv(
        daily_plan
    )

    # ----------------------------------------------
    # Display download buttons
    # ----------------------------------------------

    st.subheader("Download this plan")

    json_column, csv_column = st.columns(2)

    with json_column:

        st.download_button(
            label="Download JSON",
            data=json_download_data,
            file_name=f"{download_prefix}.json",
            mime="application/json",
            key=f"{download_prefix}_json_download",
            on_click="ignore",
            use_container_width=True,
        )

    with csv_column:

        st.download_button(
            label="Download CSV",
            data=csv_download_data,
            file_name=f"{download_prefix}.csv",
            mime="text/csv",
            key=f"{download_prefix}_csv_download",
            on_click="ignore",
            use_container_width=True,
        )


# --------------------------------------------------
# Application heading
# --------------------------------------------------

st.title("📅 Day AI Planner")

st.write(
    "Enter your schedule, important tasks, goals, "
    "and preferences. The AI will create a balanced "
    "daily plan."
)

st.caption(
    f"Current model: {get_model_name()}"
)


# --------------------------------------------------
# Main application tabs
# --------------------------------------------------

create_plan_tab, plan_history_tab = st.tabs(
    [
        "➕ Create Plan",
        "📚 Plan History",
    ]
)


# ==================================================
# TAB 1: CREATE A NEW PLAN
# ==================================================

with create_plan_tab:

    st.header(
        "Create a new daily plan"
    )

    st.caption(
        "All required fields start empty. "
        "Light example text shows what to enter."
    )

    # ----------------------------------------------
    # New-plan form
    # ----------------------------------------------

    with st.form(
        "planner_form"
    ):

        st.subheader(
            "Daily timings"
        )

        st.caption(
            "Select each time using the time picker."
        )

        left_column, right_column = st.columns(
            2
        )

        with left_column:

            # Empty time selector.
            wake_up_time = st.time_input(
                "Wake-up time",
                value=None,
                step=900,
                help="Select the time when your day begins.",
            )

            # Empty time selector.
            work_start_time = st.time_input(
                "Work start time",
                value=None,
                step=900,
                help="Select the time when work begins.",
            )

        with right_column:

            # Empty time selector.
            sleep_time = st.time_input(
                "Sleep target",
                value=None,
                step=900,
                help="Select your target bedtime.",
            )

            # Empty time selector.
            work_end_time = st.time_input(
                "Work end time",
                value=None,
                step=900,
                help="Select the time when work ends.",
            )

        st.subheader(
            "Tasks and goals"
        )

        # Empty text area with a light placeholder.
        important_tasks_text = st.text_area(
            "Important tasks",
            value="",
            placeholder=(
                "Example:\n"
                "Complete one GenAI lesson\n"
                "Apply for two jobs\n"
                "Prepare for an interview"
            ),
            help="Enter one important task per line.",
        )

        # Empty text input with a light placeholder.
        study_goal = st.text_input(
            "Study goal",
            value="",
            placeholder=(
                "Example: Study GenAI for 2 hours"
            ),
        )

        # Empty text input with a light placeholder.
        exercise_goal = st.text_input(
            "Exercise goal",
            value="",
            placeholder=(
                "Example: Walk for 30 minutes"
            ),
        )

        # Empty selection with a light placeholder.
        energy_level = st.selectbox(
            "Highest-energy period",
            options=[
                "Morning",
                "Afternoon",
                "Evening",
                "Consistent throughout the day",
            ],
            index=None,
            placeholder=(
                "Select your highest-energy period"
            ),
        )

        # Empty text area with a light placeholder.
        additional_notes = st.text_area(
            "Additional preferences",
            value="",
            placeholder=(
                "Example: Take a short break after lunch, "
                "include two coffee breaks, or schedule "
                "a walk after dinner."
            ),
        )

        submitted = st.form_submit_button(
            "Generate My Daily Plan",
            type="primary",
            use_container_width=True,
        )

    # ----------------------------------------------
    # Process submitted new-plan form
    # ----------------------------------------------

    if submitted:

        # Convert one-task-per-line text into a list.
        tasks = [
            task.strip()
            for task
            in important_tasks_text.splitlines()
            if task.strip()
        ]

        # Validate required form information.
        validation_errors = validate_user_inputs(
            wake_up_time=wake_up_time,
            sleep_time=sleep_time,
            work_start_time=work_start_time,
            work_end_time=work_end_time,
            tasks=tasks,
            study_goal=study_goal,
            energy_level=energy_level,
        )

        # Show all validation problems.
        if validation_errors:

            st.error(
                "Complete the required fields before "
                "generating your plan."
            )

            for validation_error in validation_errors:
                st.warning(validation_error)

        else:

            # Validation confirms these values are not None.
            assert wake_up_time is not None
            assert sleep_time is not None
            assert work_start_time is not None
            assert work_end_time is not None
            assert energy_level is not None

            # Convert tasks into prompt bullet points.
            formatted_tasks = "\n".join(
                f"- {task}"
                for task in tasks
            )

            # Exercise is optional.
            exercise_goal_value = (
                exercise_goal.strip()
                or "No exercise goal provided."
            )

            # Additional preferences are optional.
            additional_notes_value = (
                additional_notes.strip()
                or "No additional preferences provided."
            )

            # Build the user prompt.
            user_prompt = f"""
Create my complete daily plan.

Daily timings:
- Wake-up time: {format_time(wake_up_time)}
- Sleep target: {format_time(sleep_time)}
- Work hours: {format_time(work_start_time)}
  to {format_time(work_end_time)}

Important tasks:
{formatted_tasks}

Goals:
- Study goal: {study_goal.strip()}
- Exercise goal: {exercise_goal_value}

Energy information:
- Highest-energy period: {energy_level}

Additional preferences:
{additional_notes_value}
"""

            try:

                with st.spinner(
                    "Generating your daily plan..."
                ):

                    # Generate a structured plan through Groq.
                    daily_plan = generate_daily_plan(
                        user_prompt
                    )

                # Save the generated plan in SQLite.
                saved_plan_id = save_plan(
                    daily_plan=daily_plan,
                    model_name=get_model_name(),
                )

                st.success(
                    "Your daily plan was generated and saved "
                    f"successfully. Plan ID: {saved_plan_id}"
                )

                # Display the generated plan.
                display_daily_plan(
                    daily_plan=daily_plan,
                    download_prefix=(
                        f"daily_plan_{saved_plan_id}"
                    ),
                )

            except json.JSONDecodeError as error:

                st.error(
                    "The AI returned invalid JSON."
                )

                st.code(
                    str(error)
                )

            except Exception as error:

                st.error(
                    "The daily plan could not be generated "
                    "or saved."
                )

                st.code(
                    str(error)
                )


# ==================================================
# TAB 2: PLAN HISTORY
# ==================================================

with plan_history_tab:

    st.header(
        "Saved plan history"
    )

    st.write(
        "View, edit, download, or delete previously "
        "saved plans."
    )

    # ----------------------------------------------
    # Show update message after rerun
    # ----------------------------------------------

    update_message = st.session_state.pop(
        "update_message",
        None,
    )

    if update_message:
        st.success(update_message)

    # ----------------------------------------------
    # Show deletion message after rerun
    # ----------------------------------------------

    deletion_message = st.session_state.pop(
        "deletion_message",
        None,
    )

    if deletion_message:
        st.success(deletion_message)

    try:

        # Retrieve saved plans.
        plan_history = get_plan_history(
            limit=50
        )

        if not plan_history:

            st.info(
                "No saved plans were found. "
                "Create a plan first."
            )

        else:

            # --------------------------------------
            # Display recent plans
            # --------------------------------------

            st.subheader(
                "Recent plans"
            )

            st.dataframe(
                plan_history,
                use_container_width=True,
                hide_index=True,
            )

            # Create a lookup dictionary by Plan ID.
            history_by_id = {
                item["id"]: item
                for item in plan_history
            }

            plan_id_options = list(
                history_by_id.keys()
            )

            # --------------------------------------
            # Select a saved plan
            # --------------------------------------

            selected_plan_id = st.selectbox(
                "Select a saved plan",
                options=plan_id_options,
                format_func=lambda plan_id: (
                    f"Plan {plan_id} | "
                    f"{history_by_id[plan_id]['created_at']} | "
                    f"{history_by_id[plan_id]['summary']}"
                ),
            )

            selected_plan_id = int(
                selected_plan_id
            )

            selected_plan = get_plan_by_id(
                selected_plan_id
            )

            if selected_plan is None:

                st.error(
                    "The selected plan could not be found."
                )

            else:

                st.divider()

                st.header(
                    f"Saved Plan {selected_plan_id}"
                )

                (
                    view_plan_tab,
                    edit_plan_tab,
                    delete_plan_tab,
                ) = st.tabs(
                    [
                        "View Plan",
                        "Edit Plan",
                        "Delete Plan",
                    ]
                )

                # ==================================
                # VIEW SAVED PLAN
                # ==================================

                with view_plan_tab:

                    display_daily_plan(
                        daily_plan=selected_plan,
                        download_prefix=(
                            f"saved_plan_{selected_plan_id}"
                        ),
                        show_metadata=True,
                    )

                # ==================================
                # EDIT SAVED PLAN
                # ==================================

                with edit_plan_tab:

                    st.subheader(
                        f"Edit Plan {selected_plan_id}"
                    )

                    st.info(
                        "Enter flexible time values and click "
                        "Save Plan Changes. Times will be "
                        "normalized to h:mm AM/PM."
                    )

                    editor_version = get_editor_version(
                        selected_plan_id
                    )

                    edit_form_key = (
                        f"edit_form_{selected_plan_id}_"
                        f"{editor_version}"
                    )

                    summary_key = (
                        f"edit_summary_{selected_plan_id}_"
                        f"{editor_version}"
                    )

                    schedule_key = (
                        f"edit_schedule_{selected_plan_id}_"
                        f"{editor_version}"
                    )

                    warnings_key = (
                        f"edit_warnings_{selected_plan_id}_"
                        f"{editor_version}"
                    )

                    with st.form(
                        edit_form_key
                    ):

                        edited_summary = st.text_area(
                            "Plan summary",
                            value=selected_plan[
                                "summary"
                            ],
                            key=summary_key,
                        )

                        st.write(
                            "Edit schedule"
                        )

                        edited_schedule_data = st.data_editor(
                            selected_plan[
                                "schedule"
                            ],
                            num_rows="dynamic",
                            hide_index=True,
                            use_container_width=True,
                            column_order=[
                                "start_time",
                                "end_time",
                                "activity",
                                "priority",
                                "category",
                                "notes",
                            ],
                            column_config={
                                "start_time": (
                                    st.column_config.TextColumn(
                                        "Start Time",
                                        help=(
                                            "Examples: 9.45, "
                                            "9:45 AM, or 14:30"
                                        ),
                                        required=True,
                                    )
                                ),
                                "end_time": (
                                    st.column_config.TextColumn(
                                        "End Time",
                                        help=(
                                            "Examples: 10.15, "
                                            "10;15 AM, or 22:15"
                                        ),
                                        required=True,
                                    )
                                ),
                                "activity": (
                                    st.column_config.TextColumn(
                                        "Activity",
                                        required=True,
                                    )
                                ),
                                "priority": (
                                    st.column_config.SelectboxColumn(
                                        "Priority",
                                        options=[
                                            "High",
                                            "Medium",
                                            "Low",
                                        ],
                                        required=True,
                                    )
                                ),
                                "category": (
                                    st.column_config.TextColumn(
                                        "Category",
                                        required=True,
                                    )
                                ),
                                "notes": (
                                    st.column_config.TextColumn(
                                        "Notes",
                                    )
                                ),
                            },
                            key=schedule_key,
                        )

                        edited_warnings_text = st.text_area(
                            "Warnings",
                            value="\n".join(
                                str(warning)
                                for warning
                                in selected_plan.get(
                                    "warnings",
                                    [],
                                )
                            ),
                            placeholder=(
                                "Example: Schedule may be busy."
                            ),
                            key=warnings_key,
                        )

                        save_changes_clicked = (
                            st.form_submit_button(
                                "Save Plan Changes",
                                type="primary",
                                use_container_width=True,
                            )
                        )

                    if save_changes_clicked:

                        try:

                            # Normalize edited schedule times.
                            edited_schedule = (
                                normalize_edited_schedule(
                                    edited_schedule_data,
                                    reference_schedule=(
                                        selected_plan[
                                            "schedule"
                                        ]
                                    ),
                                )
                            )

                            # Convert warnings into a list.
                            edited_warnings = [
                                warning.strip()
                                for warning
                                in edited_warnings_text.splitlines()
                                if warning.strip()
                            ]

                            edited_plan = {
                                "summary": (
                                    edited_summary.strip()
                                ),
                                "schedule": edited_schedule,
                                "warnings": edited_warnings,
                            }

                            # Validate the edited plan.
                            validate_plan(
                                edited_plan
                            )

                            # Save changes in SQLite.
                            was_updated = update_plan(
                                plan_id=selected_plan_id,
                                daily_plan=edited_plan,
                            )

                            if was_updated:

                                advance_editor_version(
                                    selected_plan_id
                                )

                                st.session_state[
                                    "update_message"
                                ] = (
                                    f"Plan {selected_plan_id} "
                                    "was updated successfully."
                                )

                                st.rerun()

                            else:

                                st.error(
                                    "The selected plan was not found."
                                )

                        except Exception as update_error:

                            st.error(
                                "The plan changes could not be saved."
                            )

                            st.code(
                                str(update_error)
                            )

                # ==================================
                # DELETE SAVED PLAN
                # ==================================

                with delete_plan_tab:

                    st.subheader(
                        f"Delete Plan {selected_plan_id}"
                    )

                    st.warning(
                        f"Deleting Plan {selected_plan_id} is "
                        "permanent and cannot be reversed."
                    )

                    deletion_confirmed = st.checkbox(
                        (
                            "I understand that this will "
                            f"permanently delete Plan "
                            f"{selected_plan_id}."
                        ),
                        key=(
                            f"confirm_delete_"
                            f"{selected_plan_id}"
                        ),
                    )

                    delete_clicked = st.button(
                        label=(
                            f"Delete Plan {selected_plan_id}"
                        ),
                        type="primary",
                        disabled=not deletion_confirmed,
                        key=(
                            f"delete_button_"
                            f"{selected_plan_id}"
                        ),
                        use_container_width=True,
                    )

                    if delete_clicked:

                        try:

                            was_deleted = delete_plan(
                                selected_plan_id
                            )

                            if was_deleted:

                                st.session_state[
                                    "deletion_message"
                                ] = (
                                    f"Plan {selected_plan_id} "
                                    "was deleted successfully."
                                )

                                st.rerun()

                            else:

                                st.error(
                                    "The selected plan was not found."
                                )

                        except Exception as delete_error:

                            st.error(
                                "The selected plan could not "
                                "be deleted."
                            )

                            st.code(
                                str(delete_error)
                            )

    except Exception as error:

        st.error(
            "Plan history could not be loaded."
        )

        st.code(
            str(error)
        )