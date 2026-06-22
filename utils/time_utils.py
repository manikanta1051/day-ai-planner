"""
Time Utility Module for the Day AI Planner

Purpose:
    Accept flexible user-entered time values and convert them
    into one consistent format.

Standard output format:
    h:mm AM
    h:mm PM

Accepted examples:
    10.15
    10.15am
    10.15 AM
    10;15 am
    10:15
    1015
    14:30
    2.45 pm

This module is used for:
    1. AI-generated schedule times.
    2. User-edited schedule times.
"""

import re
from datetime import time
from typing import Any


# --------------------------------------------------
# Function: Format minutes as AM/PM time
# --------------------------------------------------

def minutes_to_time_text(
    total_minutes: int,
) -> str:
    """
    Convert minutes after midnight into h:mm AM/PM format.

    Parameters:
        total_minutes:
            Number of minutes after midnight.

    Returns:
        str:
            Time formatted as h:mm AM/PM.

    Examples:
        480 becomes 8:00 AM.
        870 becomes 2:30 PM.
    """

    if total_minutes < 0 or total_minutes >= 1440:
        raise ValueError(
            "Time minutes must be between 0 and 1439."
        )

    hour_24 = total_minutes // 60
    minute = total_minutes % 60

    if hour_24 == 0:
        display_hour = 12
        period = "AM"

    elif hour_24 < 12:
        display_hour = hour_24
        period = "AM"

    elif hour_24 == 12:
        display_hour = 12
        period = "PM"

    else:
        display_hour = hour_24 - 12
        period = "PM"

    return f"{display_hour}:{minute:02d} {period}"


# --------------------------------------------------
# Function: Parse flexible time text
# --------------------------------------------------

def parse_flexible_time(
    value: Any,
) -> tuple[int, int, str | None]:
    """
    Parse a flexible time value into hour, minute, and period.

    Parameters:
        value:
            User-entered or AI-generated time value.

    Returns:
        tuple:
            hour
            minute
            explicit AM/PM period or None

    Examples:
        "10.15am" returns:
            10, 15, "AM"

        "14:30" returns:
            14, 30, None

        "1015" returns:
            10, 15, None
    """

    # Python time objects can be handled directly.
    if isinstance(value, time):

        return (
            value.hour,
            value.minute,
            None,
        )

    if value is None:
        raise ValueError(
            "Time cannot be empty."
        )

    # Convert the value into uppercase text.
    text = str(value).strip().upper()

    if not text:
        raise ValueError(
            "Time cannot be empty."
        )

    # Normalize variations such as:
    # A.M. → AM
    # A M  → AM
    # P.M. → PM
    # P M  → PM
    text = re.sub(
        r"A\s*\.?\s*M\.?",
        "AM",
        text,
    )

    text = re.sub(
        r"P\s*\.?\s*M\.?",
        "PM",
        text,
    )

    # Convert alternative separators into a colon.
    #
    # Examples:
    # 10.15 → 10:15
    # 10;15 → 10:15
    text = text.replace(
        ".",
        ":",
    )

    text = text.replace(
        ";",
        ":",
    )

    # Remove spaces.
    #
    # Example:
    # 10 : 15 AM → 10:15AM
    text = re.sub(
        r"\s+",
        "",
        text,
    )

    # Read an explicitly entered period.
    explicit_period: str | None = None

    if text.endswith("AM"):

        explicit_period = "AM"
        text = text[:-2]

    elif text.endswith("PM"):

        explicit_period = "PM"
        text = text[:-2]

    # Only digits and one optional colon are allowed.
    if not re.fullmatch(
        r"\d{1,4}(?::\d{1,2})?",
        text,
    ):
        raise ValueError(
            f"'{value}' is not a recognized time. "
            "Examples: 10:15 AM, 10.15am, 1015, or 14:30."
        )

    # ----------------------------------------------
    # Separate hour and minute
    # ----------------------------------------------

    if ":" in text:

        time_parts = text.split(":")

        if len(time_parts) != 2:
            raise ValueError(
                f"'{value}' contains too many separators."
            )

        hour_text = time_parts[0]
        minute_text = time_parts[1]

    else:

        # Values containing one or two digits are
        # treated as full hours.
        #
        # Examples:
        # 8  → 8:00
        # 10 → 10:00
        if len(text) <= 2:

            hour_text = text
            minute_text = "0"

        # Three or four digits use the last two digits
        # as minutes.
        #
        # Examples:
        # 930  → 9:30
        # 1015 → 10:15
        elif len(text) in {
            3,
            4,
        }:

            hour_text = text[:-2]
            minute_text = text[-2:]

        else:

            raise ValueError(
                f"'{value}' is not a valid time."
            )

    hour = int(hour_text)
    minute = int(minute_text)

    # Minutes must always be between 00 and 59.
    if minute < 0 or minute > 59:
        raise ValueError(
            f"'{value}' contains invalid minutes. "
            "Minutes must be between 00 and 59."
        )

    # Explicit AM/PM values must use hours 1 through 12.
    if explicit_period is not None:

        if hour < 1 or hour > 12:
            raise ValueError(
                f"'{value}' contains an invalid AM/PM hour. "
                "Use an hour between 1 and 12."
            )

    # Values without AM/PM may use 24-hour format.
    else:

        if hour < 0 or hour > 23:
            raise ValueError(
                f"'{value}' contains an invalid hour. "
                "Use an hour between 0 and 23."
            )

    return (
        hour,
        minute,
        explicit_period,
    )


# --------------------------------------------------
# Function: Convert parsed time into possible minutes
# --------------------------------------------------

def build_time_candidates(
    hour: int,
    minute: int,
    explicit_period: str | None,
    preferred_period: str | None = None,
) -> list[int]:
    """
    Build possible interpretations of a time.

    A value such as 10:15 without AM or PM may mean:
        10:15 AM
        10:15 PM

    The schedule context is later used to select the
    interpretation that fits chronologically.

    Parameters:
        hour:
            Parsed hour.

        minute:
            Parsed minute.

        explicit_period:
            AM, PM, or None.

        preferred_period:
            Preferred AM/PM based on the original row
            or surrounding schedule.

    Returns:
        list[int]:
            Possible times represented as minutes
            after midnight.
    """

    # ----------------------------------------------
    # Explicit AM or PM
    # ----------------------------------------------

    if explicit_period is not None:

        if explicit_period == "AM":

            hour_24 = (
                0
                if hour == 12
                else hour
            )

        else:

            hour_24 = (
                12
                if hour == 12
                else hour + 12
            )

        return [
            hour_24 * 60 + minute
        ]

    # ----------------------------------------------
    # Unambiguous 24-hour value
    # ----------------------------------------------

    if hour == 0 or hour > 12:

        return [
            hour * 60 + minute
        ]

    # ----------------------------------------------
    # Ambiguous 1–12 hour without AM/PM
    # ----------------------------------------------

    am_hour = (
        0
        if hour == 12
        else hour
    )

    pm_hour = (
        12
        if hour == 12
        else hour + 12
    )

    am_minutes = am_hour * 60 + minute
    pm_minutes = pm_hour * 60 + minute

    normalized_preference = (
        preferred_period.upper()
        if preferred_period
        else None
    )

    # Put the preferred interpretation first.
    if normalized_preference == "PM":

        return [
            pm_minutes,
            am_minutes,
        ]

    if normalized_preference == "AM":

        return [
            am_minutes,
            pm_minutes,
        ]

    # Without context, morning is tried first.
    return [
        am_minutes,
        pm_minutes,
    ]


# --------------------------------------------------
# Function: Normalize one flexible time value
# --------------------------------------------------

def normalize_time_text(
    value: Any,
    preferred_period: str | None = None,
    earliest_minutes: int | None = None,
) -> str:
    """
    Convert a flexible time value into h:mm AM/PM format.

    Parameters:
        value:
            Flexible time input.

        preferred_period:
            Preferred AM or PM interpretation.

        earliest_minutes:
            Earliest valid time in minutes after midnight.

            This helps preserve chronological order.

    Returns:
        str:
            Normalized time.

    Raises:
        ValueError:
            When no valid interpretation exists.
    """

    (
        hour,
        minute,
        explicit_period,
    ) = parse_flexible_time(
        value
    )

    candidates = build_time_candidates(
        hour=hour,
        minute=minute,
        explicit_period=explicit_period,
        preferred_period=preferred_period,
    )

    # Find the first candidate that satisfies
    # the chronological requirement.
    for candidate_minutes in candidates:

        if (
            earliest_minutes is None
            or candidate_minutes >= earliest_minutes
        ):
            return minutes_to_time_text(
                candidate_minutes
            )

    raise ValueError(
        f"'{value}' cannot be placed at this point "
        "in the schedule without creating an invalid "
        "or overlapping time."
    )


# --------------------------------------------------
# Function: Convert normalized time into minutes
# --------------------------------------------------

def time_text_to_minutes(
    normalized_time: str,
) -> int:
    """
    Convert normalized h:mm AM/PM text into minutes.

    Parameters:
        normalized_time:
            Normalized time string.

    Returns:
        int:
            Minutes after midnight.
    """

    match = re.fullmatch(
        r"(\d{1,2}):(\d{2})\s(AM|PM)",
        normalized_time,
    )

    if match is None:
        raise ValueError(
            f"'{normalized_time}' is not in h:mm AM/PM format."
        )

    hour = int(
        match.group(1)
    )

    minute = int(
        match.group(2)
    )

    period = match.group(3)

    if hour < 1 or hour > 12:
        raise ValueError(
            "Normalized hour must be between 1 and 12."
        )

    if minute < 0 or minute > 59:
        raise ValueError(
            "Normalized minutes must be between 00 and 59."
        )

    if period == "AM":

        hour_24 = (
            0
            if hour == 12
            else hour
        )

    else:

        hour_24 = (
            12
            if hour == 12
            else hour + 12
        )

    return (
        hour_24 * 60
        + minute
    )


# --------------------------------------------------
# Function: Read AM or PM from an existing value
# --------------------------------------------------

def get_time_period(
    value: Any,
) -> str | None:
    """
    Return AM or PM from an existing time value.

    Parameters:
        value:
            Stored or generated time.

    Returns:
        str | None:
            AM, PM, or None.
    """

    try:

        normalized_value = normalize_time_text(
            value
        )

        return normalized_value.rsplit(
            " ",
            maxsplit=1,
        )[-1]

    except ValueError:

        return None


# --------------------------------------------------
# Function: Convert editor output into rows
# --------------------------------------------------

def editor_data_to_rows(
    edited_schedule_data: Any,
) -> list[dict[str, Any]]:
    """
    Convert Streamlit data-editor output into dictionaries.

    Parameters:
        edited_schedule_data:
            Data returned by st.data_editor.

    Returns:
        list[dict]:
            Schedule rows.
    """

    if isinstance(
        edited_schedule_data,
        list,
    ):
        return edited_schedule_data

    # Support pandas DataFrame output.
    if hasattr(
        edited_schedule_data,
        "to_dict",
    ):
        return edited_schedule_data.to_dict(
            orient="records"
        )

    raise TypeError(
        "The schedule editor returned an unsupported format."
    )


# --------------------------------------------------
# Function: Normalize all schedule rows
# --------------------------------------------------

def normalize_schedule_rows(
    schedule_data: Any,
    reference_schedule: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """
    Normalize and validate a complete schedule.

    This function is used for both:
        1. AI-generated schedules.
        2. User-edited schedules.

    Parameters:
        schedule_data:
            List or DataFrame containing schedule rows.

        reference_schedule:
            Original schedule used to preserve AM/PM
            when a user removes the suffix during editing.

    Returns:
        list[dict[str, str]]:
            Clean schedule with standardized time values.

    Validation performed:
        - Required fields exist.
        - Times are valid.
        - Times follow h:mm AM/PM format.
        - End time is after start time.
        - Rows are chronological.
        - Rows do not overlap.
        - Priority is valid.
    """

    raw_rows = editor_data_to_rows(
        schedule_data
    )

    original_rows = (
        reference_schedule
        if reference_schedule is not None
        else []
    )

    schedule_fields = [
        "start_time",
        "end_time",
        "activity",
        "priority",
        "category",
        "notes",
    ]

    required_fields = [
        "start_time",
        "end_time",
        "activity",
        "priority",
        "category",
    ]

    allowed_priorities = {
        "High",
        "Medium",
        "Low",
    }

    normalized_schedule: list[dict[str, str]] = []

    previous_end_minutes: int | None = None
    previous_end_period: str | None = None

    for row_number, raw_row in enumerate(
        raw_rows,
        start=1,
    ):

        if not isinstance(raw_row, dict):
            raise TypeError(
                f"Schedule row {row_number} must be an object."
            )

        cleaned_row: dict[str, str] = {}

        # Convert all values into clean strings.
        for field_name in schedule_fields:

            raw_value = raw_row.get(
                field_name,
                "",
            )

            cleaned_row[field_name] = (
                ""
                if raw_value is None
                else str(raw_value).strip()
            )

        # Ignore a completely empty row created by
        # the dynamic data editor.
        if not any(cleaned_row.values()):
            continue

        # Validate required fields before parsing.
        for required_field in required_fields:

            if not cleaned_row[required_field]:

                readable_name = required_field.replace(
                    "_",
                    " ",
                ).title()

                raise ValueError(
                    f"Row {row_number}: "
                    f"{readable_name} cannot be empty."
                )

        # Get the corresponding original row when editing.
        reference_row: dict[str, Any] = {}

        reference_index = row_number - 1

        if reference_index < len(original_rows):

            possible_reference = original_rows[
                reference_index
            ]

            if isinstance(
                possible_reference,
                dict,
            ):
                reference_row = possible_reference

        original_start_period = get_time_period(
            reference_row.get(
                "start_time"
            )
        )

        original_end_period = get_time_period(
            reference_row.get(
                "end_time"
            )
        )

        preferred_start_period = (
            original_start_period
            or previous_end_period
        )

        # Start time may equal the previous row's end time.
        normalized_start = normalize_time_text(
            value=cleaned_row["start_time"],
            preferred_period=preferred_start_period,
            earliest_minutes=previous_end_minutes,
        )

        start_minutes = time_text_to_minutes(
            normalized_start
        )

        start_period = get_time_period(
            normalized_start
        )

        preferred_end_period = (
            original_end_period
            or start_period
        )

        # End time must be at least one minute
        # later than start time.
        normalized_end = normalize_time_text(
            value=cleaned_row["end_time"],
            preferred_period=preferred_end_period,
            earliest_minutes=start_minutes + 1,
        )

        end_minutes = time_text_to_minutes(
            normalized_end
        )

        # Additional overlap protection.
        if (
            previous_end_minutes is not None
            and start_minutes < previous_end_minutes
        ):
            raise ValueError(
                f"Row {row_number} overlaps the previous activity."
            )

        # Validate priority.
        if cleaned_row["priority"] not in allowed_priorities:
            raise ValueError(
                f"Row {row_number}: priority must be "
                "High, Medium, or Low."
            )

        # Store standardized time values.
        cleaned_row["start_time"] = normalized_start
        cleaned_row["end_time"] = normalized_end

        normalized_schedule.append(
            cleaned_row
        )

        # These values help validate the following row.
        previous_end_minutes = end_minutes
        previous_end_period = get_time_period(
            normalized_end
        )

    if not normalized_schedule:
        raise ValueError(
            "The schedule must contain at least one activity."
        )

    return normalized_schedule


# --------------------------------------------------
# Function: Normalize user-edited schedule
# --------------------------------------------------

def normalize_edited_schedule(
    edited_schedule_data: Any,
    reference_schedule: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """
    Normalize schedule data returned by st.data_editor.

    This wrapper keeps the function name already used
    inside app.py.

    Parameters:
        edited_schedule_data:
            Edited schedule table.

        reference_schedule:
            Original saved schedule.

    Returns:
        list[dict[str, str]]:
            Normalized schedule.
    """

    return normalize_schedule_rows(
        schedule_data=edited_schedule_data,
        reference_schedule=reference_schedule,
    )