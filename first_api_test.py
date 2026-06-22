import os

from dotenv import load_dotenv
from groq import Groq


# Load configuration from .env
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

# Send the first request
completion = client.chat.completions.create(
    model=model_name,
    messages=[
        {
            "role": "user",
            "content": (
                "Reply with exactly: "
                "Groq API connection successful."
            ),
        }
    ],
    temperature=0,
)

# Extract and display the model's response
response_text = completion.choices[0].message.content

print(response_text)