#code file handles all validation.
from datetime import time
from typing import Any


def validate_user_inputs(
    wake_up_time: time,
    sleep_time: time,
    work_start_time: time,
    work_end_time: time,
    tasks: list[str],
    study_goal: str,
) -> list[str]:
    """Return validation errors found in the user's input."""

    errors: list[str] = []

    if wake_up_time >= sleep_time:
        errors.append(
            "Sleep time must be later than wake-up time."
        )

    if work_start_time >= work_end_time:
        errors.append(
            "Work end time must be later than work start time."
        )

    if not tasks:
        errors.append(
            "Enter at least one important task."
        )

    if not study_goal.strip():
        errors.append(
            "Enter a study goal."
        )

    return errors


def validate_plan(plan: dict[str, Any]) -> None:
    """Validate the structure returned by the LLM."""

    required_fields = {
        "summary",
        "schedule",
        "warnings",
    }

    missing_fields = required_fields - plan.keys()

    if missing_fields:
        raise ValueError(
            "The response is missing: "
            + ", ".join(sorted(missing_fields))
        )

    if not isinstance(plan["summary"], str):
        raise TypeError(
            "The summary must be text."
        )

    if not isinstance(plan["schedule"], list):
        raise TypeError(
            "The schedule must be a list."
        )

    if not isinstance(plan["warnings"], list):
        raise TypeError(
            "Warnings must be a list."
        )

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

    for index, item in enumerate(
        plan["schedule"],
        start=1,
    ):
        if not isinstance(item, dict):
            raise TypeError(
                f"Schedule item {index} must be an object."
            )

        missing_item_fields = (
            required_schedule_fields - item.keys()
        )

        if missing_item_fields:
            raise ValueError(
                f"Schedule item {index} is missing: "
                + ", ".join(sorted(missing_item_fields))
            )

        if item["priority"] not in allowed_priorities:
            raise ValueError(
                f"Schedule item {index} has an invalid priority."
            )