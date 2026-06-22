import json
import os

from dotenv import load_dotenv
from groq import Groq


# Load GROQ_API_KEY and GROQ_MODEL from .env
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model_name = os.getenv(
    "GROQ_MODEL",
    "llama-3.1-8b-instant",
)

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY was not found in the .env file."
    )


# Create the Groq client
client = Groq(api_key=api_key)


# Temporary test data
# Later, the user will enter these values through Streamlit.
wake_up_time = "8:00 AM"
work_hours = "10:00 AM to 6:00 PM"
important_tasks = [
    "Complete GenAI learning",
    "Apply for two jobs",
]
study_goal = "Study GenAI for 2 hours"
exercise_goal = "Walk for 30 minutes"
energy_level = "Low in the morning and high in the evening"
sleep_target = "11:30 PM"


# System prompt controls the assistant's behavior
system_prompt = """
You are a realistic daily productivity planner.

Create a balanced full-day schedule using only the information
provided by the user.

Rules:
- Include wake-up time, meals, work, breaks, study, and exercise.
- Do not create overlapping activities.
- Do not overload the user.
- Place difficult tasks during the user's high-energy period.
- Keep every activity between the wake-up and sleep times.
- Use High, Medium, or Low for priority.
- Return only valid JSON.
- Do not add Markdown or explanations outside the JSON.

Use this exact JSON structure:

{
  "summary": "Short description of the day",
  "schedule": [
    {
      "start_time": "8:00 AM",
      "end_time": "8:30 AM",
      "activity": "Activity description",
      "priority": "High",
      "category": "Personal",
      "notes": "Short useful note"
    }
  ],
  "warnings": []
}
"""


# User prompt contains the user's information
user_prompt = f"""
Create my complete daily plan.

Wake-up time: {wake_up_time}
Work hours: {work_hours}
Important tasks: {", ".join(important_tasks)}
Study goal: {study_goal}
Exercise goal: {exercise_goal}
Energy level: {energy_level}
Sleep target: {sleep_target}
"""


try:
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.2,
        response_format={
            "type": "json_object",
        },
    )

    response_text = completion.choices[0].message.content

    if not response_text:
        raise RuntimeError(
            "The model returned an empty response."
        )

    # Convert the JSON text into a Python dictionary
    daily_plan = json.loads(response_text)

    # Basic structure validation
    if "summary" not in daily_plan:
        raise ValueError(
            "The response is missing the 'summary' field."
        )

    if "schedule" not in daily_plan:
        raise ValueError(
            "The response is missing the 'schedule' field."
        )

    if not isinstance(daily_plan["schedule"], list):
        raise TypeError(
            "The 'schedule' field must be a list."
        )

    print("\nDaily plan generated successfully:\n")
    print(json.dumps(daily_plan, indent=2))

except json.JSONDecodeError as error:
    print("The model did not return valid JSON.")
    print(f"JSON error: {error}")

except Exception as error:
    print("The daily plan could not be generated.")
    print(f"Error: {error}")