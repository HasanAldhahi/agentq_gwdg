import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API configuration
API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL = "https://chat-ai.academiccloud.de/v1"
MODEL = "qwen3-32b"

print("--- LLM Connection Test ---")

if not API_KEY:
    print("Error: OPENAI_API_KEY not found. Please set it in your .env file.")
else:
    print(f"Using Model: {MODEL}")
    print(f"Using Base URL: {BASE_URL}")
    
    try:
        # Start OpenAI client
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        
        print("\nSending request to LLM...")
        # Get response
        chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "How tall is the Eiffel tower?"}
                ],
                response_format={"type": "json_object"},
                model=MODEL,
                # timeout=30, # Adding a timeout
            )
        
        print("\nLLM Response Received:")
        print(chat_completion.choices[0].message)
        print("\n--- Test Successful ---")

    except Exception as e:
        print(f"\n--- Test Failed ---")
        print(f"An error occurred: {e}") 