"""
Validation utilities for the Day AI Planner.

Purpose:
    Validate user-entered form information and validate
    the structured daily plan returned by the AI model.

Main functions:
    validate_user_inputs()
        Validates the Streamlit form before calling Groq.

    validate_plan()
        Validates the JSON structure returned by Groq or
        edited by the user.
"""

from datetime import time
from typing import Any


# --------------------------------------------------
# Function: Validate new-plan form inputs
# --------------------------------------------------

def validate_user_inputs(
    wake_up_time: time | None,
    sleep_time: time | None,
    work_start_time: time | None,
    work_end_time: time | None,
    tasks: list[str],
    study_goal: str | None,
    energy_level: str | None,
) -> list[str]:
    """
    Validate values entered in the Create Plan form.

    Parameters:
        wake_up_time:
            Time when the user wants to wake up.
            None means no time has been selected.

        sleep_time:
            Target bedtime.
            None means no time has been selected.

        work_start_time:
            Beginning of the user's work period.
            None means no time has been selected.

        work_end_time:
            End of the user's work period.
            None means no time has been selected.

        tasks:
            Important tasks entered one per line.

        study_goal:
            User's study goal.

        energy_level:
            Period when the user normally has the
            highest energy.

    Returns:
        list[str]:
            A list of validation messages.

            An empty list means all required values
            passed validation.
    """

    errors: list[str] = []

    # ----------------------------------------------
    # Validate required time fields
    # ----------------------------------------------

    if wake_up_time is None:
        errors.append(
            "Select a wake-up time."
        )

    if sleep_time is None:
        errors.append(
            "Select a sleep target."
        )

    if work_start_time is None:
        errors.append(
            "Select a work start time."
        )

    if work_end_time is None:
        errors.append(
            "Select a work end time."
        )

    # ----------------------------------------------
    # Compare wake-up and sleep times
    # ----------------------------------------------

    # Only compare the values when both were selected.
    if (
        wake_up_time is not None
        and sleep_time is not None
        and wake_up_time >= sleep_time
    ):
        errors.append(
            "Sleep time must be later than wake-up time."
        )

    # ----------------------------------------------
    # Compare work start and work end times
    # ----------------------------------------------

    # Only compare the values when both were selected.
    if (
        work_start_time is not None
        and work_end_time is not None
        and work_start_time >= work_end_time
    ):
        errors.append(
            "Work end time must be later than work start time."
        )

    # ----------------------------------------------
    # Validate work hours against the day
    # ----------------------------------------------

    if (
        wake_up_time is not None
        and work_start_time is not None
        and work_start_time < wake_up_time
    ):
        errors.append(
            "Work start time cannot be earlier than wake-up time."
        )

    if (
        sleep_time is not None
        and work_end_time is not None
        and work_end_time > sleep_time
    ):
        errors.append(
            "Work end time cannot be later than the sleep target."
        )

    # ----------------------------------------------
    # Validate important tasks
    # ----------------------------------------------

    if not tasks:
        errors.append(
            "Enter at least one important task."
        )

    # ----------------------------------------------
    # Validate study goal
    # ----------------------------------------------

    cleaned_study_goal = (
        study_goal.strip()
        if isinstance(study_goal, str)
        else ""
    )

    if not cleaned_study_goal:
        errors.append(
            "Enter a study goal."
        )

    # ----------------------------------------------
    # Validate energy selection
    # ----------------------------------------------

    if not energy_level:
        errors.append(
            "Select your highest-energy period."
        )

    return errors


# --------------------------------------------------
# Function: Validate generated or edited plan
# --------------------------------------------------

def validate_plan(
    plan: dict[str, Any],
) -> None:
    """
    Validate the structure of a complete daily plan.

    This function is used for:
        1. AI-generated plans.
        2. User-edited saved plans.
        3. Plans before database storage.

    Parameters:
        plan:
            Dictionary containing:
                summary
                schedule
                warnings

    Returns:
        None

    Raises:
        TypeError:
            When a value has the wrong data type.

        ValueError:
            When required data is missing or invalid.
    """

    # ----------------------------------------------
    # Validate top-level plan object
    # ----------------------------------------------

    if not isinstance(plan, dict):
        raise TypeError(
            "The daily plan must be a dictionary."
        )

    required_top_level_fields = {
        "summary",
        "schedule",
        "warnings",
    }

    missing_top_level_fields = (
        required_top_level_fields - plan.keys()
    )

    if missing_top_level_fields:
        raise ValueError(
            "The plan is missing these fields: "
            + ", ".join(
                sorted(missing_top_level_fields)
            )
        )

    # ----------------------------------------------
    # Validate summary
    # ----------------------------------------------

    if not isinstance(
        plan["summary"],
        str,
    ):
        raise TypeError(
            "The plan summary must be text."
        )

    if not plan["summary"].strip():
        raise ValueError(
            "The plan summary cannot be empty."
        )

    # ----------------------------------------------
    # Validate schedule
    # ----------------------------------------------

    if not isinstance(
        plan["schedule"],
        list,
    ):
        raise TypeError(
            "The plan schedule must be a list."
        )

    if not plan["schedule"]:
        raise ValueError(
            "The plan schedule must contain at least one activity."
        )

    # ----------------------------------------------
    # Validate warnings
    # ----------------------------------------------

    if not isinstance(
        plan["warnings"],
        list,
    ):
        raise TypeError(
            "Plan warnings must be a list."
        )

    # ----------------------------------------------
    # Schedule validation configuration
    # ----------------------------------------------

    required_schedule_fields = {
        "start_time",
        "end_time",
        "activity",
        "priority",
        "category",
        "notes",
    }

    allowed_priorities = {
        "High",
        "Medium",
        "Low",
    }

    # ----------------------------------------------
    # Validate every schedule activity
    # ----------------------------------------------

    for row_number, schedule_item in enumerate(
        plan["schedule"],
        start=1,
    ):

        if not isinstance(
            schedule_item,
            dict,
        ):
            raise TypeError(
                f"Schedule row {row_number} must be an object."
            )

        missing_schedule_fields = (
            required_schedule_fields
            - schedule_item.keys()
        )

        if missing_schedule_fields:
            raise ValueError(
                f"Schedule row {row_number} is missing: "
                + ", ".join(
                    sorted(missing_schedule_fields)
                )
            )

        # Validate every field as text.
        for field_name in required_schedule_fields:

            field_value = schedule_item[
                field_name
            ]

            if not isinstance(
                field_value,
                str,
            ):
                raise TypeError(
                    f"Schedule row {row_number}: "
                    f"{field_name} must be text."
                )

        # Required fields cannot be empty.
        required_non_empty_fields = [
            "start_time",
            "end_time",
            "activity",
            "priority",
            "category",
        ]

        for field_name in required_non_empty_fields:

            if not schedule_item[
                field_name
            ].strip():
                raise ValueError(
                    f"Schedule row {row_number}: "
                    f"{field_name} cannot be empty."
                )

        # Priority must use one of the supported values.
        if (
            schedule_item["priority"]
            not in allowed_priorities
        ):
            raise ValueError(
                f"Schedule row {row_number}: priority must "
                "be High, Medium, or Low."
            )