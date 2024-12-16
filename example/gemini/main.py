from google import genai
from dotenv import load_dotenv
import os
import asyncio
from rich.console import Console
import re

# Load environment variables
load_dotenv()

# Initialize the client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1alpha'},
)
model_id = "gemini-2.0-flash-exp"
config = {"response_modalities": ["TEXT"]}

# Initialize rich console
console = Console()


async def main():
    console.print("[cyan]Welcome to the Gemini chat! Type 'quit' to exit.[/cyan]")

    # Start the conversation session
    async with client.aio.live.connect(model=model_id, config=config) as session:
        while True:
            # Get user input
            user_message = input("> You: ").strip()

            # Exit if the user types 'quit'
            if user_message.lower() == "quit":
                console.print("[green]Goodbye![/green]")
                break

            # Send the user message to Gemini
            await session.send(user_message, end_of_turn=True)

            # Receive and print the response from Gemini
            console.print("[bold]Gemini:[/bold]")
            async for response in session.receive():
                # Check if the response has text
                if response.text:
                    console.print(response.text)
                    

            console.print("\n")  # Add a newline for readability between turns

if __name__ == "__main__":
    asyncio.run(main())
