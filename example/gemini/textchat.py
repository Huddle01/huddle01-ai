import asyncio
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Initialize the client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1alpha'},
)
model_id = "gemini-2.0-flash-exp"
config = {"response_modalities": ["TEXT"]}

conf = types.GenerateContentConfig(
        system_instruction='I say high, you say low',
        temperature= 0.3,
        response_modalities=['TEXT', 'AUDIO'],
    ),


async def main():
    print("Welcome to the Gemini chat! Type 'quit' to exit.")

    # Start the conversation session
    async with client.aio.live.connect(model=model_id, config=config) as session:
        while True:
            # Get user input
            user_message = input("> You: ").strip()

            # Exit if the user types 'quit'
            if user_message.lower() == "quit":
                print("Goodbye!")
                break

            # Send the user message to Gemini
            await session.send(user_message, end_of_turn=True)

            # Receive and print the response from Gemini
            print("Gemini: ", end="", flush=True)
            async for response in session.receive():
                print(response.text, end="", flush=True)

            print("\n")  # Add a newline for readability between turns

if __name__ == "__main__":
    asyncio.run(main())
