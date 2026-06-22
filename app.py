"""
Day AI Planner - Main Streamlit Application

Purpose:
    Provide the browser interface for creating, saving,
    viewing, editing, downloading, and deleting daily plans.

Main features:
    1. Generate personalized plans using Groq.
    2. Save generated plans into SQLite.
    3. Display saved-plan history.
    4. Edit saved schedules.
    5. Normalize flexible time entries.
    6. Refresh edited values after saving.
    7. Download plans as JSON and CSV.
    8. Delete saved plans.

Important time behavior:
    Values such as:
        9.45
        9;45
        945
        9.45am

    are converted after the user clicks:
        Save Plan Changes

    Example:
        9.45 becomes 9:45 AM
"""

import json
from datetime import time
from typing import Any

import streamlit as st

# --------------------------------------------------
# Import database functions
# --------------------------------------------------

from database.database_service import (
    delete_plan,
    get_plan_by_id,
    get_plan_history,
    save_plan,
    update_plan,
)

# --------------------------------------------------
# Import Groq planning functions
# --------------------------------------------------

from services.planner_service import (
    generate_daily_plan,
    get_model_name,
)

# --------------------------------------------------
# Import export functions
# --------------------------------------------------

from utils.exporters import (
    plan_to_csv,
    plan_to_json,
)

# --------------------------------------------------
# Import time-normalization function
# --------------------------------------------------

from utils.time_utils import (
    normalize_edited_schedule,
)

# --------------------------------------------------
# Import validation functions
# --------------------------------------------------

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
# Function: Format form time
# --------------------------------------------------

def format_time(value: time) -> str:
    """
    Convert a Python time object into AM/PM text.

    Parameters:
        value:
            Time selected through st.time_input.

    Returns:
        str:
            Time in h:mm AM/PM format.

    Example:
        08:00:00 becomes 8:00 AM.
        18:30:00 becomes 6:30 PM.
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
    Return the current editor version for a saved plan.

    Why this is required:
        Streamlit widgets preserve their values when the same
        widget key is used during a rerun.

        After saving normalized values, we increase the editor
        version. This gives the editor a new key and forces it
        to reload the updated database values.

    Parameters:
        plan_id:
            Database ID of the selected plan.

    Returns:
        int:
            Current editor version number.
    """

    # Create a separate Session State variable
    # for each saved plan.
    version_state_key = (
        f"edit_form_version_{plan_id}"
    )

    # Start at version zero when the plan has
    # not been edited during this browser session.
    if version_state_key not in st.session_state:
        st.session_state[
            version_state_key
        ] = 0

    return int(
        st.session_state[
            version_state_key
        ]
    )


# --------------------------------------------------
# Function: Refresh editor after database update
# --------------------------------------------------

def advance_editor_version(
    plan_id: int,
) -> None:
    """
    Increase the editor version after saving changes.

    Increasing the version changes the keys used by:
        - Summary text area
        - Schedule data editor
        - Warnings text area
        - Edit form

    Streamlit then creates fresh widgets using the
    normalized values loaded from SQLite.

    Parameters:
        plan_id:
            Database ID of the updated plan.

    Returns:
        None
    """

    version_state_key = (
        f"edit_form_version_{plan_id}"
    )

    current_version = int(
        st.session_state.get(
            version_state_key,
            0,
        )
    )

    # Increase the version so the next rerun
    # uses completely new widget keys.
    st.session_state[
        version_state_key
    ] = current_version + 1


# --------------------------------------------------
# Function: Display one daily plan
# --------------------------------------------------

def display_daily_plan(
    daily_plan: dict[str, Any],
    download_prefix: str,
    show_metadata: bool = False,
) -> None:
    """
    Display one generated or saved daily plan.

    This function displays:
        - Plan metadata
        - Summary
        - Schedule
        - Warnings
        - Raw JSON
        - JSON download
        - CSV download

    Parameters:
        daily_plan:
            Dictionary containing the plan.

        download_prefix:
            Prefix used for download filenames and
            Streamlit widget keys.

        show_metadata:
            When True, display Plan ID, creation time,
            and model name.

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
    # Display schedule table
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
            key=(
                f"{download_prefix}_"
                "json_download"
            ),
            on_click="ignore",
            use_container_width=True,
        )

    with csv_column:

        st.download_button(
            label="Download CSV",
            data=csv_download_data,
            file_name=f"{download_prefix}.csv",
            mime="text/csv",
            key=(
                f"{download_prefix}_"
                "csv_download"
            ),
            on_click="ignore",
            use_container_width=True,
        )


# --------------------------------------------------
# Application heading
# --------------------------------------------------

st.title("📅 Day AI Planner")

st.write(
    "Create personalized daily schedules and manage "
    "previously saved plans."
)

st.caption(
    f"Current model: {get_model_name()}"
)


# --------------------------------------------------
# Main navigation tabs
# --------------------------------------------------

create_plan_tab, plan_history_tab = st.tabs(
    [
        "➕ Create Plan",
        "📚 Plan History",
    ]
)


# ==================================================
# TAB 1: CREATE PLAN
# ==================================================

with create_plan_tab:

    st.header(
        "Create a new daily plan"
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

        left_column, right_column = st.columns(
            2
        )

        with left_column:

            # User's wake-up time.
            wake_up_time = st.time_input(
                "Wake-up time",
                value=time(
                    8,
                    0,
                ),
            )

            # Beginning of user's work schedule.
            work_start_time = st.time_input(
                "Work start time",
                value=time(
                    10,
                    0,
                ),
            )

        with right_column:

            # User's target bedtime.
            sleep_time = st.time_input(
                "Sleep target",
                value=time(
                    23,
                    30,
                ),
            )

            # End of user's work schedule.
            work_end_time = st.time_input(
                "Work end time",
                value=time(
                    18,
                    0,
                ),
            )

        st.subheader(
            "Tasks and goals"
        )

        # Enter one important task on each line.
        important_tasks_text = st.text_area(
            "Important tasks",
            value=(
                "Complete GenAI learning\n"
                "Apply for two jobs\n"
                "Prepare for interview"
            ),
            help="Enter one task per line.",
        )

        # User's study objective.
        study_goal = st.text_input(
            "Study goal",
            value="Study GenAI for 2 hours",
        )

        # User's exercise objective.
        exercise_goal = st.text_input(
            "Exercise goal",
            value="Walk for 30 minutes",
        )

        # Period when the user has the most energy.
        energy_level = st.selectbox(
            "Highest-energy period",
            options=[
                "Morning",
                "Afternoon",
                "Evening",
                "Consistent throughout the day",
            ],
            index=2,
        )

        # Optional personal scheduling instructions.
        additional_notes = st.text_area(
            "Additional preferences",
            placeholder=(
                "Example: Keep the morning light, "
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
    # Process new-plan form
    # ----------------------------------------------

    if submitted:

        # Convert multiline task text into a list.
        tasks = [
            task.strip()
            for task
            in important_tasks_text.splitlines()
            if task.strip()
        ]

        # Validate user-entered values.
        validation_errors = validate_user_inputs(
            wake_up_time=wake_up_time,
            sleep_time=sleep_time,
            work_start_time=work_start_time,
            work_end_time=work_end_time,
            tasks=tasks,
            study_goal=study_goal,
        )

        if validation_errors:

            for validation_error in validation_errors:
                st.error(
                    validation_error
                )

        else:

            # Convert task list into prompt bullet points.
            formatted_tasks = "\n".join(
                f"- {task}"
                for task in tasks
            )

            exercise_goal_value = (
                exercise_goal.strip()
                or "No exercise goal provided."
            )

            additional_notes_value = (
                additional_notes.strip()
                or "No additional preferences provided."
            )

            # Build the complete user prompt.
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

                    # Generate and normalize the schedule.
                    daily_plan = generate_daily_plan(
                        user_prompt
                    )

                # Save the generated schedule in SQLite.
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
        "View, edit, download, or delete "
        "previously saved plans."
    )

    # ----------------------------------------------
    # Show update message after rerun
    # ----------------------------------------------

    update_message = st.session_state.pop(
        "update_message",
        None,
    )

    if update_message:
        st.success(
            update_message
        )

    # ----------------------------------------------
    # Show deletion message after rerun
    # ----------------------------------------------

    deletion_message = st.session_state.pop(
        "deletion_message",
        None,
    )

    if deletion_message:
        st.success(
            deletion_message
        )

    try:

        # Load recent saved plans.
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
            # Display history table
            # --------------------------------------

            st.subheader(
                "Recent plans"
            )

            st.dataframe(
                plan_history,
                use_container_width=True,
                hide_index=True,
            )

            # Create a lookup dictionary using Plan ID.
            history_by_id = {
                history_item["id"]: history_item
                for history_item in plan_history
            }

            plan_id_options = list(
                history_by_id.keys()
            )

            # --------------------------------------
            # Select one saved plan
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

            # Retrieve complete selected-plan information.
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
                    view_saved_plan_tab,
                    edit_saved_plan_tab,
                    delete_saved_plan_tab,
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

                with view_saved_plan_tab:

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

                with edit_saved_plan_tab:

                    st.subheader(
                        f"Edit Plan {selected_plan_id}"
                    )

                    st.info(
                        "Enter flexible time values and click "
                        "Save Plan Changes. The saved values will "
                        "then be displayed in h:mm AM/PM format."
                    )

                    st.caption(
                        "Accepted examples: 9.45, 9;45, 945, "
                        "9.45am, 9:45 AM, and 14:30."
                    )

                    # Get the current editor version.
                    editor_version = get_editor_version(
                        selected_plan_id
                    )

                    # Build fresh widget keys using the version.
                    edit_form_key = (
                        f"edit_plan_form_"
                        f"{selected_plan_id}_"
                        f"{editor_version}"
                    )

                    summary_widget_key = (
                        f"edit_summary_"
                        f"{selected_plan_id}_"
                        f"{editor_version}"
                    )

                    schedule_widget_key = (
                        f"edit_schedule_"
                        f"{selected_plan_id}_"
                        f"{editor_version}"
                    )

                    warnings_widget_key = (
                        f"edit_warnings_"
                        f"{selected_plan_id}_"
                        f"{editor_version}"
                    )

                    # ----------------------------------
                    # Edit form
                    # ----------------------------------

                    with st.form(
                        edit_form_key
                    ):

                        # Edit plan summary.
                        edited_summary = st.text_area(
                            "Plan summary",
                            value=selected_plan[
                                "summary"
                            ],
                            key=summary_widget_key,
                        )

                        st.write(
                            "Edit schedule"
                        )

                        # Editable schedule table.
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
                                            "9:45 AM, 945"
                                        ),
                                        required=True,
                                    )
                                ),
                                "end_time": (
                                    st.column_config.TextColumn(
                                        "End Time",
                                        help=(
                                            "Examples: 10.15, "
                                            "10;15am, 22:15"
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
                                        required=False,
                                    )
                                ),
                            },
                            key=schedule_widget_key,
                        )

                        # Edit warnings.
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
                            help=(
                                "Enter one warning per line."
                            ),
                            key=warnings_widget_key,
                        )

                        # Save all edited form values.
                        save_changes_clicked = (
                            st.form_submit_button(
                                "Save Plan Changes",
                                type="primary",
                                use_container_width=True,
                            )
                        )

                    # ----------------------------------
                    # Process edited plan
                    # ----------------------------------

                    if save_changes_clicked:

                        try:

                            # Normalize flexible time values.
                            #
                            # Examples:
                            # 9.45 becomes 9:45 AM.
                            # 8.30 in an evening row becomes
                            # 8:30 PM based on schedule context.
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

                            # Build the edited plan dictionary.
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

                            # Save normalized values into SQLite.
                            was_updated = update_plan(
                                plan_id=selected_plan_id,
                                daily_plan=edited_plan,
                            )

                            if was_updated:

                                # Give widgets new keys during
                                # the following rerun.
                                advance_editor_version(
                                    selected_plan_id
                                )

                                # Store success message.
                                st.session_state[
                                    "update_message"
                                ] = (
                                    f"Plan {selected_plan_id} "
                                    "was updated successfully. "
                                    "Time values were normalized."
                                )

                                # Reload the application and
                                # retrieve fresh database values.
                                st.rerun()

                            else:

                                st.error(
                                    "The selected Plan ID "
                                    "was not found."
                                )

                        except Exception as update_error:

                            st.error(
                                "The plan changes could not "
                                "be saved."
                            )

                            st.code(
                                str(update_error)
                            )

                # ==================================
                # DELETE SAVED PLAN
                # ==================================

                with delete_saved_plan_tab:

                    st.subheader(
                        f"Delete Plan {selected_plan_id}"
                    )

                    st.warning(
                        f"Deleting Plan {selected_plan_id} is "
                        "permanent and cannot be reversed."
                    )

                    # Require explicit confirmation.
                    deletion_confirmed = st.checkbox(
                        (
                            "I understand that this will "
                            f"permanently delete Plan "
                            f"{selected_plan_id}."
                        ),
                        key=(
                            f"confirm_delete_plan_"
                            f"{selected_plan_id}"
                        ),
                    )

                    # Disable button until confirmation.
                    delete_button_clicked = st.button(
                        label=(
                            f"Delete Plan {selected_plan_id}"
                        ),
                        type="primary",
                        disabled=not deletion_confirmed,
                        key=(
                            f"delete_plan_button_"
                            f"{selected_plan_id}"
                        ),
                        use_container_width=True,
                    )

                    if delete_button_clicked:

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
                                    "The selected plan was "
                                    "not found."
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