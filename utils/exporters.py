"""
Utility functions for converting a generated daily plan
into downloadable JSON and CSV formats.
"""

import csv
import io
import json
from typing import Any


def plan_to_json(
    daily_plan: dict[str, Any],
) -> str:
    """
    Convert the complete daily plan into formatted JSON text.

    Parameters:
        daily_plan:
            The validated daily-plan dictionary returned
            by the AI model.

    Returns:
        A formatted JSON string that can be downloaded.
    """

    # indent=2 makes the downloaded JSON easier to read.
    return json.dumps(
        daily_plan,
        indent=2,
        ensure_ascii=False,
    )


def plan_to_csv(
    daily_plan: dict[str, Any],
) -> str:
    """
    Convert the schedule portion of a daily plan into CSV text.

    Parameters:
        daily_plan:
            The validated daily-plan dictionary returned
            by the AI model.

    Returns:
        CSV-formatted text containing the schedule rows.
    """

    # Create an in-memory text file.
    # Nothing is written permanently to the laptop.
    output = io.StringIO()

    # Define the exact CSV column order.
    field_names = [
        "start_time",
        "end_time",
        "activity",
        "priority",
        "category",
        "notes",
    ]

    # Create a CSV writer that accepts dictionaries.
    writer = csv.DictWriter(
        output,
        fieldnames=field_names,
    )

    # Add the column names as the first CSV row.
    writer.writeheader()

    # Read the schedule list safely.
    schedule = daily_plan.get(
        "schedule",
        [],
    )

    # Write one CSV row for every schedule item.
    for schedule_item in schedule:

        # Only include the required CSV fields.
        row = {
            field_name: schedule_item.get(
                field_name,
                "",
            )
            for field_name in field_names
        }

        writer.writerow(row)

    # Return the complete CSV content as text.
    return output.getvalue()