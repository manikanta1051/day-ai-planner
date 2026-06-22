"""
Automated tests for Day AI Planner time utilities.

Purpose:
    Verify that flexible time values are converted into
    the correct h:mm AM/PM format.

These tests protect important behaviors such as:
    1. Converting periods and semicolons into colons.
    2. Handling AM and PM text.
    3. Converting 24-hour time.
    4. Preserving an expected AM/PM period.
    5. Rejecting invalid minutes and hours.
    6. Normalizing complete schedule rows.
    7. Preventing overlapping activities.
"""

import unittest

# Import the functions being tested.
from utils.time_utils import (
    normalize_schedule_rows,
    normalize_time_text,
    time_text_to_minutes,
)


# --------------------------------------------------
# Test class: Individual time normalization
# --------------------------------------------------

class TestNormalizeTimeText(unittest.TestCase):
    """
    Test different flexible time-input formats.
    """

    def test_period_separator_with_am(self) -> None:
        """
        Verify that a period separator and lowercase AM
        are converted correctly.
        """

        result = normalize_time_text(
            "10.15am"
        )

        self.assertEqual(
            result,
            "10:15 AM",
        )

    def test_semicolon_separator_with_pm(self) -> None:
        """
        Verify that a semicolon separator is accepted.
        """

        result = normalize_time_text(
            "10;15 PM"
        )

        self.assertEqual(
            result,
            "10:15 PM",
        )

    def test_compact_four_digit_time(self) -> None:
        """
        Verify that 1015 is interpreted as 10:15 AM
        when no other period context exists.
        """

        result = normalize_time_text(
            "1015"
        )

        self.assertEqual(
            result,
            "10:15 AM",
        )

    def test_twenty_four_hour_time(self) -> None:
        """
        Verify that a 24-hour time is converted to PM.
        """

        result = normalize_time_text(
            "14.30"
        )

        self.assertEqual(
            result,
            "2:30 PM",
        )

    def test_preferred_pm_period(self) -> None:
        """
        Verify that an ambiguous value uses the supplied
        preferred PM period.
        """

        result = normalize_time_text(
            "8.30",
            preferred_period="PM",
        )

        self.assertEqual(
            result,
            "8:30 PM",
        )

    def test_full_hour_defaults_to_zero_minutes(self) -> None:
        """
        Verify that a full hour receives :00 minutes.
        """

        result = normalize_time_text(
            "7"
        )

        self.assertEqual(
            result,
            "7:00 AM",
        )

    def test_invalid_minutes_are_rejected(self) -> None:
        """
        Verify that minutes greater than 59 are rejected.
        """

        with self.assertRaises(
            ValueError
        ):
            normalize_time_text(
                "10.75"
            )

    def test_invalid_hour_is_rejected(self) -> None:
        """
        Verify that invalid 24-hour values are rejected.
        """

        with self.assertRaises(
            ValueError
        ):
            normalize_time_text(
                "25.30"
            )


# --------------------------------------------------
# Test class: Convert normalized time to minutes
# --------------------------------------------------

class TestTimeTextToMinutes(unittest.TestCase):
    """
    Test conversion from AM/PM text to minutes
    after midnight.
    """

    def test_morning_time_conversion(self) -> None:
        """
        8:30 AM should equal 510 minutes after midnight.
        """

        result = time_text_to_minutes(
            "8:30 AM"
        )

        self.assertEqual(
            result,
            510,
        )

    def test_evening_time_conversion(self) -> None:
        """
        8:30 PM should equal 1230 minutes after midnight.
        """

        result = time_text_to_minutes(
            "8:30 PM"
        )

        self.assertEqual(
            result,
            1230,
        )

    def test_midnight_conversion(self) -> None:
        """
        12:00 AM represents midnight.
        """

        result = time_text_to_minutes(
            "12:00 AM"
        )

        self.assertEqual(
            result,
            0,
        )

    def test_noon_conversion(self) -> None:
        """
        12:00 PM represents noon.
        """

        result = time_text_to_minutes(
            "12:00 PM"
        )

        self.assertEqual(
            result,
            720,
        )


# --------------------------------------------------
# Test class: Complete schedule normalization
# --------------------------------------------------

class TestNormalizeScheduleRows(unittest.TestCase):
    """
    Test normalization and validation of complete
    schedule tables.
    """

    def test_valid_morning_schedule(self) -> None:
        """
        Verify that flexible times in multiple rows
        are standardized correctly.
        """

        schedule = [
            {
                "start_time": "7",
                "end_time": "7.30",
                "activity": "Morning routine",
                "priority": "Low",
                "category": "Personal",
                "notes": "Prepare for the day",
            },
            {
                "start_time": "7.30",
                "end_time": "8",
                "activity": "Breakfast",
                "priority": "Low",
                "category": "Personal",
                "notes": "Eat breakfast",
            },
        ]

        result = normalize_schedule_rows(
            schedule
        )

        self.assertEqual(
            result[0]["start_time"],
            "7:00 AM",
        )

        self.assertEqual(
            result[0]["end_time"],
            "7:30 AM",
        )

        self.assertEqual(
            result[1]["start_time"],
            "7:30 AM",
        )

        self.assertEqual(
            result[1]["end_time"],
            "8:00 AM",
        )

    def test_valid_evening_schedule_with_reference(self) -> None:
        """
        Verify that edited values preserve PM using
        the original schedule as context.
        """

        edited_schedule = [
            {
                "start_time": "8",
                "end_time": "8.30",
                "activity": "Apply for jobs",
                "priority": "High",
                "category": "Work",
                "notes": "Submit applications",
            }
        ]

        original_schedule = [
            {
                "start_time": "8:00 PM",
                "end_time": "9:00 PM",
                "activity": "Apply for jobs",
                "priority": "High",
                "category": "Work",
                "notes": "Submit applications",
            }
        ]

        result = normalize_schedule_rows(
            schedule_data=edited_schedule,
            reference_schedule=original_schedule,
        )

        self.assertEqual(
            result[0]["start_time"],
            "8:00 PM",
        )

        self.assertEqual(
            result[0]["end_time"],
            "8:30 PM",
        )

    def test_explicit_overlap_is_rejected(self) -> None:
        """
        Verify that overlapping activities are not accepted.
        """

        schedule = [
            {
                "start_time": "8:00 AM",
                "end_time": "9:00 AM",
                "activity": "Study",
                "priority": "High",
                "category": "Study",
                "notes": "Morning study",
            },
            {
                "start_time": "8:30 AM",
                "end_time": "10:00 AM",
                "activity": "Work",
                "priority": "High",
                "category": "Work",
                "notes": "Start work",
            },
        ]

        with self.assertRaises(
            ValueError
        ):
            normalize_schedule_rows(
                schedule
            )

    def test_invalid_priority_is_rejected(self) -> None:
        """
        Verify that priority must be High, Medium, or Low.
        """

        schedule = [
            {
                "start_time": "8:00 AM",
                "end_time": "9:00 AM",
                "activity": "Study",
                "priority": "Urgent",
                "category": "Study",
                "notes": "Morning study",
            }
        ]

        with self.assertRaises(
            ValueError
        ):
            normalize_schedule_rows(
                schedule
            )

    def test_empty_schedule_is_rejected(self) -> None:
        """
        Verify that a plan cannot contain an empty schedule.
        """

        with self.assertRaises(
            ValueError
        ):
            normalize_schedule_rows(
                []
            )


# --------------------------------------------------
# Run tests directly
# --------------------------------------------------

if __name__ == "__main__":
    """
    Allow this file to run directly.

    Command:
        python tests/test_time_utils.py
    """

    unittest.main()