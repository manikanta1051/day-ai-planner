import os

from dotenv import load_dotenv


# Load variables from the .env file
load_dotenv()

# Read Groq configuration
api_key = os.getenv("GROQ_API_KEY")
model_name = os.getenv(
    "GROQ_MODEL",
    "llama-3.1-8b-instant",
)

# Validate API key
if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY was not found in the .env file."
    )

# Validate model name
if not model_name:
    raise RuntimeError(
        "GROQ_MODEL was not found in the .env file."
    )

print("Groq API configuration loaded successfully.")
print(f"Selected model: {model_name}")