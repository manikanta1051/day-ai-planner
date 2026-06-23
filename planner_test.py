import os
import json
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# ---------------------------------------------------------
# 1. Load environment variables from the .env file
# ---------------------------------------------------------
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY was not found.\n"
        "Open your .env file and add:\n"
        "GROQ_API_KEY=your_actual_groq_api_key"
    )


# ---------------------------------------------------------
# 2. Create the Groq client
# ---------------------------------------------------------
client = Groq(api_key=api_key)


# ---------------------------------------------------------
# 3. Clean the AI response before converting it to JSON
# ---------------------------------------------------------
def clean_json_response(response_text: str) -> dict:
    """
    Removes unwanted text or Markdown code blocks from the AI response
    and converts the response into a Python dictionary.
    """

    if not response_text:
        raise ValueError("The AI returned an empty response.")

    cleaned_text = response_text.strip()

    # Remove Markdown code block markers if the AI includes them
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.replace("```json", "", 1)
        cleaned_text = cleaned_text.replace("```", "", 1)

        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        cleaned_text = cleaned_text.strip()

    # Find the first opening brace and final closing brace
    first_brace = cleaned_text.find("{")
    last_brace = cleaned_text.rfind("}")

    if first_brace == -1 or last_brace == -1:
        raise ValueError(
            "The AI response did not contain a valid JSON object."
        )

    json_text = cleaned_text[first_brace:last_brace + 1]

    return json.loads(json_text)


# ---------------------------------------------------------
# 4. Validate the generated daily plan
# ---------------------------------------------------------
def validate_daily_plan(plan: dict) -> None:
    """
    Checks whether the generated plan contains the required structure.
    """

    if not isinstance(plan, dict):
        raise ValueError("The generated daily plan must be a JSON object.")

    if "summary" not in plan:
        raise ValueError("The daily plan is missing the 'summary' field.")

    if "schedule" not in plan:
        raise ValueError("The daily plan is missing the 'schedule' field.")

    if not isinstance(plan["schedule"], list):
        raise ValueError("The 'schedule' field must contain a list.")

    required_fields = [
        "start_time",
        "end_time",
        "activity",
        "priority",
        "category",
        "notes",
    ]

    for item_number, schedule_item in enumerate(
        plan["schedule"],
        start=1,
    ):
        if not isinstance(schedule_item, dict):
            raise ValueError(
                f"Schedule item {item_number} must be a JSON object."
            )

        for field in required_fields:
            if field not in schedule_item:
                raise ValueError(
                    f"Schedule item {item_number} is missing "
                    f"the '{field}' field."
                )


# ---------------------------------------------------------
# 5. Save the generated daily plan
# ---------------------------------------------------------
def save_daily_plan(plan: dict) -> None:
    """
    Saves the new daily plan inside data/daily_plans.json.
    Existing plans are preserved.
    """

    file_path = Path("data/daily_plans.json")

    # Create the data folder if it does not exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing plans
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                plans = json.load(file)

            # Make sure the existing data is a list
            if not isinstance(plans, list):
                plans = []

        except (json.JSONDecodeError, OSError):
            plans = []
    else:
        plans = []

    # Create a copy before adding the date
    plan_to_save = plan.copy()

    # Add today's date
    plan_to_save["date"] = date.today().isoformat()

    # Add the new plan
    plans.append(plan_to_save)

    # Save all plans
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(
            plans,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\nDaily plan saved successfully.")
    print(f"Saved file: {file_path.resolve()}")


# ---------------------------------------------------------
# 6. Information used to generate the daily plan
# ---------------------------------------------------------
user_details = """
Wake-up time: 8:00 AM
Sleep time: 11:30 PM

Main goals:
- Study GenAI for 3 hours
- Apply for jobs for 2 hours
- Exercise for 1 hour
- Include breakfast, lunch and dinner
- Include reasonable rest breaks
"""


# ---------------------------------------------------------
# 7. Prompt sent to the AI model
# ---------------------------------------------------------
prompt = f"""
Create a realistic daily plan using the following user information:

{user_details}

Return only one valid JSON object.

Use exactly this structure:

{{
    "summary": "Short summary of the daily plan",
    "schedule": [
        {{
            "start_time": "8:00 AM",
            "end_time": "8:30 AM",
            "activity": "Morning routine",
            "priority": "Low",
            "category": "Personal",
            "notes": "Drink water and prepare for the day"
        }}
    ]
}}

Important rules:

1. Return only valid JSON.
2. Do not use Markdown code blocks.
3. Do not write any explanation before or after the JSON.
4. Every schedule item must contain:
   start_time, end_time, activity, priority, category and notes.
5. Do not create overlapping activities.
6. Keep the activities between the wake-up time and sleep time.
7. Include meals, breaks and personal activities.
8. Priority must be High, Medium or Low.
"""


# ---------------------------------------------------------
# 8. Generate, validate, display and save the daily plan
# ---------------------------------------------------------
def main() -> None:
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a daily planning assistant. "
                        "Return only valid JSON without Markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
        )

        response_text = response.choices[0].message.content

        # Convert the AI response into a Python dictionary
        daily_plan = clean_json_response(response_text)

        # Check the required JSON structure
        validate_daily_plan(daily_plan)

        # Display the generated plan
        print("\nDaily plan generated successfully:\n")
        print(
            json.dumps(
                daily_plan,
                indent=4,
                ensure_ascii=False,
            )
        )

        # Save the generated plan
        save_daily_plan(daily_plan)

    except json.JSONDecodeError as error:
        print("\nThe AI response was not valid JSON.")
        print(f"Error details: {error}")

    except ValueError as error:
        print("\nThe generated plan could not be processed.")
        print(f"Error details: {error}")

    except Exception as error:
        print("\nAn error occurred while generating the daily plan.")
        print(f"Error details: {error}")


# ---------------------------------------------------------
# 9. Start the program
# ---------------------------------------------------------
if __name__ == "__main__":
    main()