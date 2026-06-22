"""
Groq Planning Service for the Day AI Planner

Purpose:
    Communicate with the Groq API, generate a structured
    daily plan, normalize schedule times, and validate
    the final response.

Main processing flow:
    User prompt
        ↓
    Groq API request
        ↓
    JSON response
        ↓
    Parse JSON
        ↓
    Normalize schedule times
        ↓
    Validate final structure
        ↓
    Return daily plan

Reliability feature:
    When Groq fails to generate valid JSON, this module
    automatically retries the request with stronger
    JSON-formatting instructions.
"""

import json
import os
from typing import Any

from dotenv import load_dotenv
from groq import (
    BadRequestError,
    Groq,
)

# Import the main AI system prompt.
from prompts.planner_prompts import SYSTEM_PROMPT

# Import schedule-time normalization.
from utils.time_utils import normalize_schedule_rows

# Import response-structure validation.
from utils.validators import validate_plan


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# Retry configuration
# --------------------------------------------------

# Maximum number of Groq requests made when JSON
# generation or response validation fails.
MAX_GENERATION_ATTEMPTS = 3


# Different temperatures are used for each attempt.
#
# Attempt 1:
#     Normal generation.
#
# Attempt 2:
#     Less randomness.
#
# Attempt 3:
#     Most consistent output.
ATTEMPT_TEMPERATURES = {
    1: 0.2,
    2: 0.1,
    3: 0.0,
}


# Extra instruction added after the first failure.
#
# This reminds the model to produce only one valid
# JSON object without Markdown or comments.
JSON_RETRY_INSTRUCTION = """
IMPORTANT JSON REQUIREMENTS:

Your previous response could not be processed as valid JSON.

Generate the complete plan again.

Strict rules:
- Return exactly one JSON object.
- Start the response with { and end it with }.
- Use double quotes around every JSON key and string.
- Do not use single quotes.
- Do not add Markdown code fences.
- Do not add explanations before or after the JSON.
- Do not add comments inside the JSON.
- Do not use trailing commas.
- Include summary, schedule, and warnings.
- Every schedule item must contain all required fields.
- All schedule times must use the format h:mm AM or h:mm PM.
- Keep the schedule in chronological order.
- Do not create overlapping activities.

Required structure:

{
  "summary": "Short description of the day",
  "schedule": [
    {
      "start_time": "8:00 AM",
      "end_time": "8:30 AM",
      "activity": "Morning routine",
      "priority": "Low",
      "category": "Personal",
      "notes": "Prepare for the day"
    }
  ],
  "warnings": []
}
"""


# --------------------------------------------------
# Function: Get configured model name
# --------------------------------------------------

def get_model_name() -> str:
    """
    Return the model configured in the .env file.

    Returns:
        str:
            Groq model name.

    Default:
        llama-3.1-8b-instant
    """

    return os.getenv(
        "GROQ_MODEL",
        "llama-3.1-8b-instant",
    )


# --------------------------------------------------
# Function: Create Groq client
# --------------------------------------------------

def create_groq_client() -> Groq:
    """
    Create and return an authenticated Groq client.

    Returns:
        Groq:
            Configured Groq API client.

    Raises:
        RuntimeError:
            When GROQ_API_KEY is missing.
    """

    # Read the private API key from the .env file.
    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    # Stop when the API key is unavailable.
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY was not found in the .env file."
        )

    # Create the Groq client.
    return Groq(
        api_key=api_key
    )


# --------------------------------------------------
# Function: Build messages for one attempt
# --------------------------------------------------

def build_messages(
    user_prompt: str,
    attempt_number: int,
) -> list[dict[str, str]]:
    """
    Build the system and user messages sent to Groq.

    Parameters:
        user_prompt:
            User's timings, tasks, goals, and preferences.

        attempt_number:
            Current generation attempt.

    Returns:
        list[dict[str, str]]:
            Messages ready for the Groq API.
    """

    # First attempt uses the normal system prompt.
    system_content = SYSTEM_PROMPT

    # Retry attempts receive stronger JSON instructions.
    if attempt_number > 1:
        system_content = (
            f"{SYSTEM_PROMPT}\n\n"
            f"{JSON_RETRY_INSTRUCTION}"
        )

    return [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


# --------------------------------------------------
# Function: Check for Groq JSON-generation failure
# --------------------------------------------------

def is_json_generation_error(
    error: BadRequestError,
) -> bool:
    """
    Check whether a Groq 400 error was caused by
    failed JSON generation.

    Parameters:
        error:
            BadRequestError returned by the Groq SDK.

    Returns:
        bool:
            True when the error appears related to
            JSON generation.

            False for other types of 400 errors.
    """

    # Convert the complete error into lowercase text
    # so the check is not case-sensitive.
    error_text = str(
        error
    ).lower()

    return (
        "failed to generate json" in error_text
        or "failed_generation" in error_text
    )


# --------------------------------------------------
# Function: Send one Groq request
# --------------------------------------------------

def request_plan_completion(
    client: Groq,
    user_prompt: str,
    attempt_number: int,
) -> Any:
    """
    Send one plan-generation request to Groq.

    Parameters:
        client:
            Authenticated Groq client.

        user_prompt:
            User information used to build the schedule.

        attempt_number:
            Current retry attempt.

    Returns:
        Any:
            Groq completion response.
    """

    # Get the temperature configured for this attempt.
    temperature = ATTEMPT_TEMPERATURES.get(
        attempt_number,
        0.0,
    )

    # Send the request in JSON Object Mode.
    return client.chat.completions.create(
        model=get_model_name(),
        messages=build_messages(
            user_prompt=user_prompt,
            attempt_number=attempt_number,
        ),
        temperature=temperature,
        response_format={
            "type": "json_object",
        },
    )


# --------------------------------------------------
# Function: Extract model response
# --------------------------------------------------

def extract_response_text(
    completion: Any,
) -> str:
    """
    Extract the generated JSON text from Groq.

    Parameters:
        completion:
            Groq completion response.

    Returns:
        str:
            Generated JSON text.

    Raises:
        RuntimeError:
            When the model returns no content.
    """

    response_text = (
        completion.choices[0].message.content
    )

    if not response_text:
        raise RuntimeError(
            "The model returned an empty response."
        )

    return response_text.strip()


# --------------------------------------------------
# Function: Parse and prepare generated plan
# --------------------------------------------------

def parse_and_prepare_plan(
    response_text: str,
) -> dict[str, Any]:
    """
    Parse, normalize, and validate a generated plan.

    Parameters:
        response_text:
            JSON text returned by Groq.

    Returns:
        dict[str, Any]:
            Final validated daily plan.

    Processing:
        1. Convert JSON text into Python data.
        2. Validate the original response.
        3. Normalize every schedule time.
        4. Validate the normalized response.
    """

    # Convert JSON text into a Python dictionary.
    daily_plan = json.loads(
        response_text
    )

    # The top-level JSON value must be an object.
    if not isinstance(
        daily_plan,
        dict,
    ):
        raise TypeError(
            "The AI response must be a JSON object."
        )

    # Validate required fields before normalization.
    validate_plan(
        daily_plan
    )

    # Normalize schedule times.
    #
    # Examples:
    # 10.15am becomes 10:15 AM.
    # 14:30 becomes 2:30 PM.
    normalized_schedule = normalize_schedule_rows(
        daily_plan["schedule"]
    )

    # Replace raw schedule with standardized schedule.
    daily_plan["schedule"] = normalized_schedule

    # Validate the final plan again.
    validate_plan(
        daily_plan
    )

    return daily_plan


# --------------------------------------------------
# Function: Generate daily plan with retries
# --------------------------------------------------

def generate_daily_plan(
    user_prompt: str,
) -> dict[str, Any]:
    """
    Generate a personalized daily plan through Groq.

    The request is attempted up to three times when:
        - Groq fails to generate valid JSON.
        - The response contains malformed JSON.
        - The generated structure is invalid.
        - The generated schedule has invalid times.

    Parameters:
        user_prompt:
            User timings, tasks, goals, energy level,
            and additional preferences.

    Returns:
        dict[str, Any]:
            Parsed, normalized, and validated plan.

    Raises:
        RuntimeError:
            When all generation attempts fail.
    """

    # Validate the prompt data type.
    if not isinstance(
        user_prompt,
        str,
    ):
        raise TypeError(
            "The user prompt must be text."
        )

    # Prevent empty requests.
    if not user_prompt.strip():
        raise ValueError(
            "The user prompt cannot be empty."
        )

    # Create the authenticated Groq client.
    client = create_groq_client()

    # Store the most recent error for debugging.
    last_error: Exception | None = None

    # Attempt generation up to the configured maximum.
    for attempt_number in range(
        1,
        MAX_GENERATION_ATTEMPTS + 1,
    ):

        try:

            # Send one request to Groq.
            completion = request_plan_completion(
                client=client,
                user_prompt=user_prompt.strip(),
                attempt_number=attempt_number,
            )

            # Extract the generated JSON text.
            response_text = extract_response_text(
                completion
            )

            # Parse, normalize, and validate the plan.
            return parse_and_prepare_plan(
                response_text
            )

        except BadRequestError as error:

            # Save the error for the final message.
            last_error = error

            # Retry only when Groq failed to generate JSON.
            if not is_json_generation_error(
                error
            ):
                raise

            # Continue to the next attempt when one remains.
            if attempt_number < MAX_GENERATION_ATTEMPTS:
                continue

        except (
            json.JSONDecodeError,
            ValueError,
            TypeError,
        ) as error:

            # These errors indicate that Groq returned
            # unusable JSON, invalid fields, or bad times.
            last_error = error

            # Try generating a cleaner response.
            if attempt_number < MAX_GENERATION_ATTEMPTS:
                continue

    # All attempts failed.
    raise RuntimeError(
        "Groq could not generate a valid daily-plan JSON "
        f"after {MAX_GENERATION_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    )