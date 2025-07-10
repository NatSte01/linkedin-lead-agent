# LinkedIn Lead Generation Agent

An autonomous agent that scrapes LinkedIn for qualified leads using Selenium and qualifies them with a local Large Language Model (LLM) via Ollama.

## Features

-   **Automated Scraping**: Logs into LinkedIn, performs searches, and scrolls through results.
-   **Human-like Behavior**: Uses randomized delays and actions to reduce the risk of detection.
-   **AI-Powered Qualification**: Leverages a local LLM (via Ollama) to analyze post text and determine if it's a qualified lead, saving you time.
-   **Configurable**: Easily change search queries, lead goals, date filters, and the LLM model used.
-   **Resume Sessions**: The agent remembers which posts it has already processed, allowing you to stop and start without creating duplicates.
-   **CSV Output**: Saves all found leads to a clean `.csv` file for easy use.

---

### ⚠️ Disclaimer

Automating social media interactions is against the Terms of Service of most platforms, including LinkedIn. **Use this script at your own risk.** The authors are not responsible for any account restrictions, suspensions, or bans that may occur. This tool is intended for educational purposes.

Furthermore, LinkedIn frequently updates its website structure. The Selenium selectors in this script may break over time. You might need to update them in the `SELECTORS` dictionary in `lead_agent.py`.

---

## Prerequisites

Before you begin, ensure you have the following installed:

1.  **Python 3.8+**
2.  **Google Chrome** browser
3.  **[Ollama](https://ollama.com/)**: You must have the Ollama server installed and running on your local machine.
4.  **An Ollama Model**: The agent needs a model to perform the qualification. You can pull one from the command line. This script is configured for `deepseek-r1:8b`, but you can use others like `llama3` or `mistral`.
    ```bash
    ollama pull deepseek-r1:8b
    ```
5.  **A LinkedIn Account**

---

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/linkedin-lead-agent.git
    cd linkedin-lead-agent
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create your environment file:**
    Copy the example file to create your own `.env` file.
    ```bash
    cp .env.example .env
    ```

5.  **Add your credentials:**
    Open the newly created `.env` file and add your LinkedIn email and password.
    ```
    LINKEDIN_EMAIL="your_linkedin_email@example.com"
    LINKEDIN_PASSWORD="your_linkedin_password"
    ```
    The `.gitignore` file is configured to prevent this file from ever being committed to Git.

---

## Configuration

You can customize the agent's behavior by editing the configuration variables at the top of `lead_agent.py`:

-   `AGENT_GOAL`: A high-level description of the agent's goal (for logging).
-   `OLLAMA_MODEL_NAME`: The Ollama model to use for qualification (must be pulled locally).
-   `LEAD_GOAL_COUNT`: The number of qualified leads the agent should find before stopping.
-   `OUTPUT_FILE`: The name of the CSV file where leads will be saved.
-   `SEARCH_QUERIES`: A Python list of search terms to use on LinkedIn.
-   `DATE_FILTER`: Filter posts by date. Options: `"past-24h"`, `"past-week"`, `"past-month"`, `"any"`.

---

## How to Run

1.  **Ensure Ollama is running** in a separate terminal or as a background service.
2.  Activate your virtual environment (if you haven't already).
3.  Run the agent from your terminal:
    ```bash
    python lead_agent.py
    ```

The agent will open a Chrome browser, log in, and begin its search. You will see its progress logged in the console. If a CAPTCHA is detected, the script will pause and ask for your intervention.

The found leads will be saved in `linkedin_leads.csv` (or your configured output file).
