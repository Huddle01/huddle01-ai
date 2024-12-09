# Setup Instructions

This guide provides step-by-step instructions to set up the project on your local machine. The project uses [Poetry](https://python-poetry.org/) for dependency management and incorporates `huddle01-ai` internally.

---

## Prerequisites

Before proceeding, ensure you have the following installed on your system:

1. **Install Python**:
   - Version: `>=3.12`
   - [Download Python](https://www.python.org/downloads/)

   Confirm installation:
   ```bash
   python --version
   ```

2. **Install Poetry**:

    Install Poetry:
    ```bash
    curl -sSL https://install.python-poetry.org | python -
    ```
    
    Confirm installation:
    ```bash
    poetry --version
    ```

    If facing issues, refer [Poetry Installation Guide](https://python-poetry.org/docs/#installation)

3. **Clone the Repository**:

    Clone the repository to your local machine:
    ```bash
    git clone git@github.com:Huddle01/huddle01-ai.git
    ```

4. **Navigate to the Project Directory**:

    ```bash
    cd huddle01-ai
    ```

🎉 You have successfully done set up of the project on your local machine!

---

## Environment Variables

Create a `.env` file in the root of the project and add the following environment variables:

```bash
HUDDLE_PROJECT_ID=
HUDDLE_API_KEY=
OPENAI_API_KEY=
```

You can get the `HUDDLE_PROJECT_ID` and `HUDDLE_API_KEY` from the [Huddle01 Developer Console](https://huddle01.dev).

For `OPENAI` and `GOOGLE_CLOUD_PROJECT`, you can get the API keys from the respective provider's console.

## Installation

1. **Install Dependencies**:

    Install dependencies using Poetry:
    ```bash
    poetry install
    ```

2. **Activate Virtual Environment**:
    
        Activate the virtual environment:
        ```bash
        poetry shell
        ```

3. **Run the Example Chatbot**:

    Run the Chatbot:
    ```bash
    poetry run python -m example.chatbot.main
    ```

    The chatbot will start running in the terminal, and you can interact with it by going on the `shinigami.huddle01.com` and joining the room.

---

## Remarks

The project is under active development, and we are actively looking for contributors to help us build this project, if you are facing any issues or have any suggestions, feel free to open an issue or PR.

You can also join the Huddle01 Discord Community for any queries or discussions.

Discord: [Huddle01 Discord Community](https://discord.gg/huddle01)

---


