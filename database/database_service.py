"""
SQLite Database Service for the Day AI Planner

Purpose:
    This module manages all database operations for saved plans.

Main responsibilities:
    1. Create the SQLite database.
    2. Create the plans table.
    3. Save generated plans.
    4. Retrieve plan history.
    5. Retrieve one plan by its ID.
    6. Update an existing saved plan.
    7. Delete a saved plan.

Database file:
    data/day_planner.db
"""

import json
import sqlite3
from pathlib import Path
from typing import Any


# --------------------------------------------------
# Database path configuration
# --------------------------------------------------

# __file__ points to:
# Day_AI_Planner/database/database_service.py
#
# .parent points to:
# Day_AI_Planner/database/
#
# .parent.parent points to:
# Day_AI_Planner/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Folder where the SQLite database will be stored.
DATA_FOLDER = PROJECT_ROOT / "data"


# Complete database file location.
DATABASE_PATH = DATA_FOLDER / "day_planner.db"


# --------------------------------------------------
# Function: Open the database connection
# --------------------------------------------------

def get_database_connection() -> sqlite3.Connection:
    """
    Open and return a connection to the SQLite database.

    Returns:
        sqlite3.Connection:
            An active SQLite database connection.

    Important:
        SQLite creates the database file automatically
        when it does not already exist.
    """

    # Create the data folder when it does not exist.
    DATA_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Open a connection to the SQLite database.
    connection = sqlite3.connect(
        str(DATABASE_PATH)
    )

    # Allow database columns to be accessed by name.
    #
    # Example:
    # row["summary"]
    #
    # Instead of:
    # row[2]
    connection.row_factory = sqlite3.Row

    return connection


# --------------------------------------------------
# Function: Initialize the database
# --------------------------------------------------

def initialize_database() -> None:
    """
    Create the SQLite database and plans table.

    This function is safe to run multiple times because
    it uses CREATE TABLE IF NOT EXISTS.

    Returns:
        None
    """

    # Open the database connection.
    connection = get_database_connection()

    try:

        # Create a cursor used to execute SQL commands.
        cursor = connection.cursor()

        # Create the plans table if it does not exist.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                summary TEXT NOT NULL,
                schedule_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                model_name TEXT NOT NULL
            )
            """
        )

        # Permanently save the table creation.
        connection.commit()

    finally:

        # Always close the database connection.
        connection.close()


# --------------------------------------------------
# Function: Validate plan before database storage
# --------------------------------------------------

def validate_plan_for_database(
    daily_plan: dict[str, Any],
) -> None:
    """
    Validate important plan values before saving or updating.

    Parameters:
        daily_plan:
            Dictionary containing summary, schedule,
            and warnings.

    Returns:
        None

    Raises:
        ValueError:
            When required information is empty.

        TypeError:
            When values have an incorrect data type.
    """

    # Read values from the plan.
    summary = daily_plan.get(
        "summary",
        "",
    )

    schedule = daily_plan.get(
        "schedule",
        [],
    )

    warnings = daily_plan.get(
        "warnings",
        [],
    )

    # Validate the summary.
    if not isinstance(summary, str):
        raise TypeError(
            "The plan summary must be text."
        )

    if not summary.strip():
        raise ValueError(
            "The plan summary cannot be empty."
        )

    # Validate the schedule.
    if not isinstance(schedule, list):
        raise TypeError(
            "The plan schedule must be a list."
        )

    if not schedule:
        raise ValueError(
            "The plan schedule must contain at least one item."
        )

    # Validate warnings.
    if not isinstance(warnings, list):
        raise TypeError(
            "The plan warnings must be a list."
        )


# --------------------------------------------------
# Function: Convert plan values into JSON text
# --------------------------------------------------

def prepare_plan_for_database(
    daily_plan: dict[str, Any],
) -> tuple[str, str, str]:
    """
    Prepare the plan values for SQLite storage.

    SQLite cannot directly store Python lists.
    Therefore, schedule and warnings are converted
    into JSON-formatted text.

    Parameters:
        daily_plan:
            Plan containing summary, schedule,
            and warnings.

    Returns:
        tuple[str, str, str]:
            1. Clean summary text
            2. Schedule as JSON text
            3. Warnings as JSON text
    """

    # Validate the plan before converting it.
    validate_plan_for_database(
        daily_plan
    )

    # Clean the summary.
    summary = daily_plan["summary"].strip()

    # Convert the Python schedule list into JSON text.
    schedule_json = json.dumps(
        daily_plan["schedule"],
        ensure_ascii=False,
    )

    # Convert the Python warnings list into JSON text.
    warnings_json = json.dumps(
        daily_plan.get(
            "warnings",
            [],
        ),
        ensure_ascii=False,
    )

    return (
        summary,
        schedule_json,
        warnings_json,
    )


# --------------------------------------------------
# Function: Save a new generated plan
# --------------------------------------------------

def save_plan(
    daily_plan: dict[str, Any],
    model_name: str,
) -> int:
    """
    Save a newly generated daily plan into SQLite.

    Parameters:
        daily_plan:
            The validated plan returned by the AI model.

        model_name:
            Name of the model that created the plan.

    Returns:
        int:
            The automatically generated database Plan ID.
    """

    # Ensure that the database and table exist.
    initialize_database()

    # Validate the supplied model name.
    if not isinstance(model_name, str):
        raise TypeError(
            "The model name must be text."
        )

    if not model_name.strip():
        raise ValueError(
            "The model name cannot be empty."
        )

    # Convert the plan into database-ready values.
    (
        summary,
        schedule_json,
        warnings_json,
    ) = prepare_plan_for_database(
        daily_plan
    )

    # Open the database connection.
    connection = get_database_connection()

    try:

        cursor = connection.cursor()

        # Insert the new plan.
        #
        # Question marks are SQL parameters.
        # They keep data separate from the SQL command.
        cursor.execute(
            """
            INSERT INTO plans (
                summary,
                schedule_json,
                warnings_json,
                model_name
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                summary,
                schedule_json,
                warnings_json,
                model_name.strip(),
            ),
        )

        # Permanently save the inserted record.
        connection.commit()

        # Retrieve the ID automatically created by SQLite.
        plan_id = cursor.lastrowid

        if plan_id is None:
            raise RuntimeError(
                "The plan was saved, but no Plan ID was returned."
            )

        return int(plan_id)

    finally:

        connection.close()


# --------------------------------------------------
# Function: Retrieve saved-plan history
# --------------------------------------------------

def get_plan_history(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Retrieve recently saved plans.

    Parameters:
        limit:
            Maximum number of plan records to return.

    Returns:
        list[dict[str, Any]]:
            History information for saved plans.

    History information includes:
        - Plan ID
        - Creation time
        - Summary
        - Number of schedule items
        - Model name
    """

    # Ensure the database exists.
    initialize_database()

    # Validate the history limit.
    if limit <= 0:
        raise ValueError(
            "The history limit must be greater than zero."
        )

    connection = get_database_connection()

    try:

        cursor = connection.cursor()

        # Retrieve the newest records first.
        cursor.execute(
            """
            SELECT
                id,
                created_at,
                summary,
                schedule_json,
                model_name
            FROM plans
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()

        history: list[dict[str, Any]] = []

        for row in rows:

            # Convert schedule JSON text back into a list.
            schedule = json.loads(
                row["schedule_json"]
            )

            # Add one clean history record.
            history.append(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "summary": row["summary"],
                    "schedule_item_count": len(schedule),
                    "model_name": row["model_name"],
                }
            )

        return history

    finally:

        connection.close()


# --------------------------------------------------
# Function: Retrieve one complete saved plan
# --------------------------------------------------

def get_plan_by_id(
    plan_id: int,
) -> dict[str, Any] | None:
    """
    Retrieve one complete plan using its Plan ID.

    Parameters:
        plan_id:
            Unique database ID of the saved plan.

    Returns:
        dict[str, Any]:
            Complete plan when found.

        None:
            When no matching plan exists.
    """

    # Ensure the database exists.
    initialize_database()

    # Validate the Plan ID.
    if plan_id <= 0:
        raise ValueError(
            "Plan ID must be greater than zero."
        )

    connection = get_database_connection()

    try:

        cursor = connection.cursor()

        # Retrieve the matching plan.
        cursor.execute(
            """
            SELECT
                id,
                created_at,
                summary,
                schedule_json,
                warnings_json,
                model_name
            FROM plans
            WHERE id = ?
            """,
            (plan_id,),
        )

        row = cursor.fetchone()

        # No matching record was found.
        if row is None:
            return None

        # Convert stored JSON text back into Python lists.
        schedule = json.loads(
            row["schedule_json"]
        )

        warnings = json.loads(
            row["warnings_json"]
        )

        # Return the complete plan.
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "summary": row["summary"],
            "schedule": schedule,
            "warnings": warnings,
            "model_name": row["model_name"],
        }

    finally:

        connection.close()


# --------------------------------------------------
# Function: Update an existing saved plan
# --------------------------------------------------

def update_plan(
    plan_id: int,
    daily_plan: dict[str, Any],
) -> bool:
    """
    Update an existing saved plan in SQLite.

    This function changes:
        - Summary
        - Schedule
        - Warnings

    This function does not change:
        - Plan ID
        - Original creation time
        - Model name

    Parameters:
        plan_id:
            Database ID of the plan being updated.

        daily_plan:
            Dictionary containing the edited summary,
            schedule, and warnings.

    Returns:
        bool:
            True when the plan was updated.

            False when no matching Plan ID was found.
    """

    # Ensure the database exists.
    initialize_database()

    # Validate the Plan ID.
    if plan_id <= 0:
        raise ValueError(
            "Plan ID must be greater than zero."
        )

    # Convert edited values into database-ready values.
    (
        summary,
        schedule_json,
        warnings_json,
    ) = prepare_plan_for_database(
        daily_plan
    )

    connection = get_database_connection()

    try:

        cursor = connection.cursor()

        # Update only the selected plan.
        cursor.execute(
            """
            UPDATE plans
            SET
                summary = ?,
                schedule_json = ?,
                warnings_json = ?
            WHERE id = ?
            """,
            (
                summary,
                schedule_json,
                warnings_json,
                plan_id,
            ),
        )

        # Permanently save the update.
        connection.commit()

        # rowcount tells us how many records changed.
        updated_row_count = cursor.rowcount

        return updated_row_count > 0

    finally:

        connection.close()


# --------------------------------------------------
# Function: Delete a saved plan
# --------------------------------------------------

def delete_plan(
    plan_id: int,
) -> bool:
    """
    Permanently delete one saved plan.

    Parameters:
        plan_id:
            Database ID of the plan to delete.

    Returns:
        bool:
            True when a plan was deleted.

            False when the Plan ID was not found.

    Warning:
        This operation permanently removes the plan.
    """

    # Ensure the database exists.
    initialize_database()

    # Validate the Plan ID.
    if plan_id <= 0:
        raise ValueError(
            "Plan ID must be greater than zero."
        )

    connection = get_database_connection()

    try:

        cursor = connection.cursor()

        # Delete only the selected plan.
        cursor.execute(
            """
            DELETE FROM plans
            WHERE id = ?
            """,
            (plan_id,),
        )

        # Save the deletion permanently.
        connection.commit()

        deleted_row_count = cursor.rowcount

        return deleted_row_count > 0

    finally:

        connection.close()


# --------------------------------------------------
# Direct database test
# --------------------------------------------------

if __name__ == "__main__":
    """
    This section runs only when this file is executed
    directly from the terminal.

    Command:
        python database/database_service.py
    """

    initialize_database()

    print("SQLite database initialized successfully.")
    print(f"Database location: {DATABASE_PATH}")