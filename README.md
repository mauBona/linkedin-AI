# LinkedIn Post Generation System with CrewAI

This project uses the CrewAI library and the OpenAI API (GPT-4o) to automate the creation and evaluation of LinkedIn posts focused on **Responsible AI** and the **EU AI Act**.

## Features

- **Automatic Post Generation**: A specialized AI Agent creates informative and engaging posts based on authoritative sources.
- **Controlled Structure and Style**: Posts follow a predefined structure (title, intro, body, conclusion) and a specific tone of voice (visionary and pragmatic).
- **Quality Validation**: An integrated validation system checks that each post meets requirements for length (200-300 words), hashtags (`#ResponsibleAI`, `#EUAIAct`), and readability.
- **Performance Evaluation (Simulated)**: A mechanism simulates collecting metrics from LinkedIn (likes, comments, shares) to calculate an effectiveness score.
- **Iterative Feedback Loop**: The system uses both generated and manually provided feedback to improve the quality of future posts.
- **Traceable Output**: Each generated post, along with its validation report and feedback, is saved in a timestamped JSON file.

## Prerequisites

- Python 3.8 or higher (tested with Python 3.11.6)
- An OpenAI account with an API key

## Installation and Setup

1.  **Clone the repository**:
    ```bash
    git clone <YOUR_REPOSITORY_URL>
    cd <FOLDER_NAME>
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables**:
    - Rename the file `.env.example` to `.env`.
    - Open the `.env` file and enter your OpenAI API key:
      ```env
      OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
      OPENAI_MODEL_NAME="gpt-4o"
      LINKEDIN_ACCESS_TOKEN="your_linkedin_access_token_here"
      ```
    - The `LINKEDIN_ACCESS_TOKEN` is a placeholder for future integration and is not required for running the simulation.

## Usage

To start the generation and evaluation process, run the main script:

```bash
python linkedin_crew.py
```

The script will print its progress, the generated post, the validation report, and the feedback to the console.

## Program Output

On each run, the following files will be generated or updated:

- **`post_[timestamp]_[id].json`**: A JSON file containing the newly created post, its validation report, and the effectiveness score.
- **`feedback.json`**: Contains the textual feedback generated from the evaluation. This file will be read on the next run to improve the new post.

## Providing Manual Feedback

You can guide the Generator Agent by editing the `manual_feedback.json` file. Insert your suggestions into the `manual_feedback` array. This feedback will be combined with the automatic feedback.

```json
{
  "manual_feedback": [
    "Focus more on the financial impact of non-compliance with the AI Act.",
    "Make the call-to-action more specific, perhaps by inviting to a webinar."
  ]
}
```

## Note on the LinkedIn API

The current implementation **simulates** calls to the LinkedIn API and generates dummy metrics. For a real-world application, the `get_linkedin_metrics_mock` function in `linkedin_crew.py` must be replaced with integration logic that handles OAuth 2.0 authentication and real API calls.
