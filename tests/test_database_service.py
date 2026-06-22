"""
Automated tests for the Day AI Planner SQLite database service.

Purpose:
    Verify that plans can be created, saved, retrieved,
    updated, listed, and deleted correctly.

Important safety behavior:
    These tests do not use the real application database.

    Each test uses a temporary SQLite database that is
    automatically deleted after the test finishes.

Functions tested:
    initialize_database()
    save_plan()
    get_plan_by_id()
    get_plan_history()
    update_plan()
    delete_plan()
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import the complete database module rather than
# importing individual functions.
#
# This allows the tests to temporarily replace:
# DATA_FOLDER
# DATABASE_PATH
from database import database_service


# --------------------------------------------------
# Test class: SQLite database service
# --------------------------------------------------

class TestDatabaseService(unittest.TestCase):
    """
    Test all important database operations.

    Every test receives a completely new temporary database.
    This prevents tests from changing the real day_planner.db.
    """

    # --------------------------------------------------
    # Setup before every test
    # --------------------------------------------------

    def setUp(self) -> None:
        """
        Create a temporary database before each test.

        unittest automatically runs this method before
        every test method.
        """

        # Create a temporary folder managed by Python.
        self.temporary_directory = tempfile.TemporaryDirectory()

        # Convert the temporary folder path into a Path object.
        self.temporary_data_folder = Path(
            self.temporary_directory.name
        )

        # Create the temporary database file path.
        self.temporary_database_path = (
            self.temporary_data_folder
            / "test_day_planner.db"
        )

        # Temporarily replace the real DATA_FOLDER value
        # inside database_service.py.
        self.data_folder_patcher = patch.object(
            database_service,
            "DATA_FOLDER",
            self.temporary_data_folder,
        )

        # Temporarily replace the real DATABASE_PATH value
        # inside database_service.py.
        self.database_path_patcher = patch.object(
            database_service,
            "DATABASE_PATH",
            self.temporary_database_path,
        )

        # Activate both temporary replacements.
        self.data_folder_patcher.start()
        self.database_path_patcher.start()

    # --------------------------------------------------
    # Cleanup after every test
    # --------------------------------------------------

    def tearDown(self) -> None:
        """
        Remove the temporary database after each test.

        unittest automatically runs this method after
        every test method.
        """

        # Restore the original DATA_FOLDER value.
        self.data_folder_patcher.stop()

        # Restore the original DATABASE_PATH value.
        self.database_path_patcher.stop()

        # Delete the temporary folder and database.
        self.temporary_directory.cleanup()

    # --------------------------------------------------
    # Helper: Create a valid sample plan
    # --------------------------------------------------

    def create_sample_plan(self) -> dict:
        """
        Create reusable valid plan data.

        Returns:
            dict:
                A complete plan containing summary,
                schedule, and warnings.
        """

        return {
            "summary": "Test daily plan",
            "schedule": [
                {
                    "start_time": "8:00 AM",
                    "end_time": "8:30 AM",
                    "activity": "Morning routine",
                    "priority": "Low",
                    "category": "Personal",
                    "notes": "Prepare for the day",
                },
                {
                    "start_time": "8:30 AM",
                    "end_time": "9:30 AM",
                    "activity": "Study GenAI",
                    "priority": "High",
                    "category": "Study",
                    "notes": "Complete one lesson",
                },
            ],
            "warnings": [],
        }

    # --------------------------------------------------
    # Test: Initialize database
    # --------------------------------------------------

    def test_initialize_database_creates_file_and_table(
        self,
    ) -> None:
        """
        Verify that initialization creates:
            1. The SQLite database file.
            2. The plans table.
        """

        # Create the temporary database.
        database_service.initialize_database()

        # Confirm that the database file exists.
        self.assertTrue(
            self.temporary_database_path.exists()
        )

        # Open the temporary database directly.
        connection = sqlite3.connect(
            str(self.temporary_database_path)
        )

        try:
            cursor = connection.cursor()

            # Search SQLite's internal table list.
            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'plans'
                """
            )

            table_record = cursor.fetchone()

            # Confirm that the plans table exists.
            self.assertIsNotNone(
                table_record
            )

        finally:
            connection.close()

    # --------------------------------------------------
    # Test: Save and retrieve plan
    # --------------------------------------------------

    def test_save_plan_and_retrieve_by_id(
        self,
    ) -> None:
        """
        Verify that a plan can be saved and retrieved
        using its generated Plan ID.
        """

        sample_plan = self.create_sample_plan()

        # Save the plan into the temporary database.
        plan_id = database_service.save_plan(
            daily_plan=sample_plan,
            model_name="test-model",
        )

        # The first saved plan should receive ID 1.
        self.assertEqual(
            plan_id,
            1,
        )

        # Retrieve the saved plan.
        saved_plan = database_service.get_plan_by_id(
            plan_id
        )

        # Confirm that a matching plan was found.
        self.assertIsNotNone(
            saved_plan
        )

        # This check helps Python type checking.
        if saved_plan is None:
            self.fail(
                "The saved plan could not be retrieved."
            )

        # Verify saved values.
        self.assertEqual(
            saved_plan["id"],
            plan_id,
        )

        self.assertEqual(
            saved_plan["summary"],
            sample_plan["summary"],
        )

        self.assertEqual(
            saved_plan["schedule"],
            sample_plan["schedule"],
        )

        self.assertEqual(
            saved_plan["warnings"],
            sample_plan["warnings"],
        )

        self.assertEqual(
            saved_plan["model_name"],
            "test-model",
        )

        # SQLite should generate a creation timestamp.
        self.assertTrue(
            saved_plan["created_at"]
        )

    # --------------------------------------------------
    # Test: Unknown Plan ID
    # --------------------------------------------------

    def test_get_unknown_plan_returns_none(
        self,
    ) -> None:
        """
        Verify that requesting an unknown Plan ID
        returns None instead of crashing.
        """

        database_service.initialize_database()

        result = database_service.get_plan_by_id(
            999
        )

        self.assertIsNone(
            result
        )

    # --------------------------------------------------
    # Test: Plan history
    # --------------------------------------------------

    def test_get_plan_history_returns_newest_first(
        self,
    ) -> None:
        """
        Verify that history:
            1. Returns saved plans.
            2. Returns the newest plan first.
            3. Includes the schedule-item count.
        """

        first_plan = self.create_sample_plan()
        first_plan["summary"] = "First test plan"

        second_plan = self.create_sample_plan()
        second_plan["summary"] = "Second test plan"

        first_plan_id = database_service.save_plan(
            daily_plan=first_plan,
            model_name="test-model-one",
        )

        second_plan_id = database_service.save_plan(
            daily_plan=second_plan,
            model_name="test-model-two",
        )

        history = database_service.get_plan_history(
            limit=10
        )

        # Two plans should be returned.
        self.assertEqual(
            len(history),
            2,
        )

        # The newest plan must appear first.
        self.assertEqual(
            history[0]["id"],
            second_plan_id,
        )

        self.assertEqual(
            history[1]["id"],
            first_plan_id,
        )

        # Confirm summary and model values.
        self.assertEqual(
            history[0]["summary"],
            "Second test plan",
        )

        self.assertEqual(
            history[0]["model_name"],
            "test-model-two",
        )

        # The sample plan contains two schedule rows.
        self.assertEqual(
            history[0]["schedule_item_count"],
            2,
        )

    # --------------------------------------------------
    # Test: Plan-history limit
    # --------------------------------------------------

    def test_get_plan_history_respects_limit(
        self,
    ) -> None:
        """
        Verify that the history limit controls the
        maximum number of returned plans.
        """

        for plan_number in range(
            1,
            4,
        ):
            sample_plan = self.create_sample_plan()

            sample_plan["summary"] = (
                f"Plan number {plan_number}"
            )

            database_service.save_plan(
                daily_plan=sample_plan,
                model_name="test-model",
            )

        history = database_service.get_plan_history(
            limit=2
        )

        # Only two plans should be returned.
        self.assertEqual(
            len(history),
            2,
        )

        # IDs 3 and 2 should be returned because
        # history is ordered from newest to oldest.
        self.assertEqual(
            history[0]["id"],
            3,
        )

        self.assertEqual(
            history[1]["id"],
            2,
        )

    # --------------------------------------------------
    # Test: Update saved plan
    # --------------------------------------------------

    def test_update_plan_changes_saved_values(
        self,
    ) -> None:
        """
        Verify that an existing plan can be updated.

        The update should change:
            - Summary
            - Schedule
            - Warnings
        """

        original_plan = self.create_sample_plan()

        plan_id = database_service.save_plan(
            daily_plan=original_plan,
            model_name="original-model",
        )

        updated_plan = {
            "summary": "Updated daily plan",
            "schedule": [
                {
                    "start_time": "9:00 AM",
                    "end_time": "10:00 AM",
                    "activity": "Updated activity",
                    "priority": "Medium",
                    "category": "Work",
                    "notes": "Updated notes",
                }
            ],
            "warnings": [
                "Updated warning"
            ],
        }

        was_updated = database_service.update_plan(
            plan_id=plan_id,
            daily_plan=updated_plan,
        )

        # Confirm that the database update succeeded.
        self.assertTrue(
            was_updated
        )

        saved_plan = database_service.get_plan_by_id(
            plan_id
        )

        self.assertIsNotNone(
            saved_plan
        )

        if saved_plan is None:
            self.fail(
                "The updated plan could not be retrieved."
            )

        # Confirm changed values.
        self.assertEqual(
            saved_plan["summary"],
            "Updated daily plan",
        )

        self.assertEqual(
            saved_plan["schedule"],
            updated_plan["schedule"],
        )

        self.assertEqual(
            saved_plan["warnings"],
            [
                "Updated warning"
            ],
        )

        # update_plan() should not change the model name.
        self.assertEqual(
            saved_plan["model_name"],
            "original-model",
        )

    # --------------------------------------------------
    # Test: Update unknown plan
    # --------------------------------------------------

    def test_update_unknown_plan_returns_false(
        self,
    ) -> None:
        """
        Verify that updating a missing Plan ID returns False.
        """

        database_service.initialize_database()

        result = database_service.update_plan(
            plan_id=999,
            daily_plan=self.create_sample_plan(),
        )

        self.assertFalse(
            result
        )

    # --------------------------------------------------
    # Test: Delete saved plan
    # --------------------------------------------------

    def test_delete_plan_removes_record(
        self,
    ) -> None:
        """
        Verify that a saved plan can be permanently deleted.
        """

        sample_plan = self.create_sample_plan()

        plan_id = database_service.save_plan(
            daily_plan=sample_plan,
            model_name="test-model",
        )

        # Confirm that the plan exists before deletion.
        saved_plan_before_delete = (
            database_service.get_plan_by_id(
                plan_id
            )
        )

        self.assertIsNotNone(
            saved_plan_before_delete
        )

        # Delete the plan.
        was_deleted = database_service.delete_plan(
            plan_id
        )

        self.assertTrue(
            was_deleted
        )

        # Confirm that the plan no longer exists.
        saved_plan_after_delete = (
            database_service.get_plan_by_id(
                plan_id
            )
        )

        self.assertIsNone(
            saved_plan_after_delete
        )

    # --------------------------------------------------
    # Test: Delete unknown plan
    # --------------------------------------------------

    def test_delete_unknown_plan_returns_false(
        self,
    ) -> None:
        """
        Verify that deleting a missing Plan ID
        returns False.
        """

        database_service.initialize_database()

        result = database_service.delete_plan(
            999
        )

        self.assertFalse(
            result
        )

    # --------------------------------------------------
    # Test: Reject empty summary
    # --------------------------------------------------

    def test_save_plan_rejects_empty_summary(
        self,
    ) -> None:
        """
        Verify that a plan with an empty summary
        cannot be saved.
        """

        invalid_plan = self.create_sample_plan()

        invalid_plan["summary"] = ""

        with self.assertRaises(
            ValueError
        ):
            database_service.save_plan(
                daily_plan=invalid_plan,
                model_name="test-model",
            )

    # --------------------------------------------------
    # Test: Reject empty schedule
    # --------------------------------------------------

    def test_save_plan_rejects_empty_schedule(
        self,
    ) -> None:
        """
        Verify that a plan without schedule items
        cannot be saved.
        """

        invalid_plan = self.create_sample_plan()

        invalid_plan["schedule"] = []

        with self.assertRaises(
            ValueError
        ):
            database_service.save_plan(
                daily_plan=invalid_plan,
                model_name="test-model",
            )

    # --------------------------------------------------
    # Test: Reject empty model name
    # --------------------------------------------------

    def test_save_plan_rejects_empty_model_name(
        self,
    ) -> None:
        """
        Verify that a plan cannot be saved without
        a model name.
        """

        with self.assertRaises(
            ValueError
        ):
            database_service.save_plan(
                daily_plan=self.create_sample_plan(),
                model_name="",
            )


# --------------------------------------------------
# Run this test file directly
# --------------------------------------------------

if __name__ == "__main__":
    """
    Allow this test file to run directly.

    Recommended command:
        python -m unittest tests.test_database_service -v
    """

    unittest.main()