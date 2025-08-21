# ==============================================================================
# LIBRARIES AND INITIAL SETUP
# ==============================================================================
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import textstat
import random

import requests
from bs4 import BeautifulSoup
from crewai import Agent, Task, Crew, Process
from crewai_tools import BaseTool
from langchain_openai import ChatOpenAI

# Load environment variables from the .env file
load_dotenv()

# Set the language for textstat to English
textstat.set_lang("en_US")

# ==============================================================================
# USEFUL RESOURCES AND DOCUMENTATION (as requested)
# ==============================================================================
# CrewAI Documentation: https://docs.crewai.com/
# EU AI Act: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689
# OpenAI API: https://platform.openai.com/docs/
# LinkedIn API: https://learn.microsoft.com/en-us/linkedin/shared/integrations/social-actions
# ==============================================================================


# ==============================================================================
# MODULAR SUPPORT FUNCTIONS
# ==============================================================================

def setup_llm():
    """
    Configures and returns the Large Language Model (LLM) to be used.
    Uses gpt-4o as specified, reading the API key from environment variables.
    """
    try:
        llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
            temperature=0.7  # A bit of creativity, but not too much
        )
        return llm
    except Exception as e:
        print(f"Error during LLM configuration: {e}")
        print("Please ensure you have correctly set OPENAI_API_KEY and OPENAI_MODEL_NAME in your .env file.")
        return None

def load_feedback(automatic_feedback_file="feedback.json", manual_feedback_file="feedback_manuale.json"):
    """
    Loads feedback from JSON files, both automatically generated and
    manually entered, to provide it to the Generator Agent.
    """
    feedback_points = []
    # Load automatic feedback if it exists
    if os.path.exists(automatic_feedback_file):
        try:
            with open(automatic_feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "textual_feedback" in data:
                    feedback_points.append(data["textual_feedback"])
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {automatic_feedback_file}.")


    # Load manual feedback if it exists
    if os.path.exists(manual_feedback_file):
        try:
            with open(manual_feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "manual_feedback" in data:
                    feedback_points.extend(data["manual_feedback"])
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {manual_feedback_file}.")

    if not feedback_points:
        return "No previous feedback available. Starting from scratch."

    return "\n- ".join(["Use this feedback to improve the post:"] + feedback_points)

def validate_post(post_content):
    """
    Validates a generated post against quality requirements.
    Checks: length, presence of hashtags, and readability.
    """
    print("\n--- STARTING VALIDATION REPORT ---")
    validation_report = {}

    # 1. Length Check
    word_count = len(post_content.split())
    is_length_valid = 200 <= word_count <= 300
    validation_report["word_count"] = {"count": word_count, "is_valid": is_length_valid}
    print(f"Word Count: {word_count} (Valid: {is_length_valid})")

    # 2. Hashtag Check
    required_hashtags = ["#ResponsibleAI", "#EUAIAct"]
    found_hashtags = [tag for tag in required_hashtags if tag in post_content]
    are_hashtags_valid = len(found_hashtags) == len(required_hashtags)
    validation_report["hashtags"] = {"required": required_hashtags, "found": found_hashtags, "is_valid": are_hashtags_valid}
    print(f"Required Hashtags Found: {found_hashtags} (Valid: {are_hashtags_valid})")

    # 3. Readability Check (Flesch Reading Ease)
    # Note: textstat works best on longer texts, but gives a good indication.
    # A score > 60 is considered good for a general audience.
    try:
        readability_score = textstat.flesch_reading_ease(post_content)
        is_readable = readability_score >= 60
        validation_report["readability"] = {"flesch_reading_ease_score": readability_score, "is_valid": is_readable}
        print(f"Readability Score (Flesch Reading Ease): {readability_score:.2f} (Recommended >= 60: {is_readable})")
    except Exception as e:
        print(f"Could not calculate readability: {e}")
        validation_report["readability"] = {"error": str(e)}

    # 4. Link Check
    has_links = "http://" in post_content or "https://" in post_content
    validation_report["links"] = {"found": has_links}
    print(f"Presence of external links: {has_links}")

    print("--- END OF VALIDATION REPORT ---\n")
    return validation_report

def get_linkedin_metrics_mock(post_content):
    """
    *** MOCK (SIMULATED) FUNCTION ***
    Simulates collecting metrics from the LinkedIn API.
    In a real application, this is where you would place the call to the LinkedIn API
    using an OAuth 2.0 token.
    """
    print("--- RUNNING EFFECTIVENESS EVALUATION (SIMULATED) ---")
    print("WARNING: Using FAKE data. Replace with real LinkedIn API calls.")

    # Example of authentication handling (to be implemented)
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token or access_token == "your_linkedin_access_token_here":
        print("LinkedIn access token not configured. Cannot make a real API call.")
        # In this mock, we proceed with fake data anyway.

    # Dummy data for simulation
    mock_metrics = {
        "likes": random.randint(20, 150),
        "comments": random.randint(5, 40),
        "shares": random.randint(2, 25)
    }
    print(f"Simulated metrics gathered: Likes={mock_metrics['likes']}, Comments={mock_metrics['comments']}, Shares={mock_metrics['shares']}")
    return mock_metrics

def analyze_and_generate_feedback(metrics, weights={"likes": 0.2, "comments": 0.5, "shares": 0.3}):
    """
    Calculates an effectiveness score and generates textual feedback.
    """
    # Calculate weighted score
    score = (metrics["likes"] * weights["likes"] +
             metrics["comments"] * weights["comments"] +
             metrics["shares"] * weights["shares"])

    # Generate textual feedback
    feedback_text = f"The post achieved an effectiveness score of {score:.2f}. "
    if metrics["comments"] < 10:
        feedback_text += "Engagement (comments) is low. Try asking a more direct or controversial question to stimulate discussion. "
    if metrics["shares"] < 5:
        feedback_text += "Shares are low. The content might not have been perceived as unique or useful enough. Try including an infographic or a surprising statistic. "
    if metrics["likes"] > 100:
        feedback_text += "Great number of likes, the title and intro worked well. Keep this up. "

    print(f"Calculated effectiveness score: {score:.2f}")
    print(f"Generated feedback for the next cycle: {feedback_text}")
    print("--- END OF EFFECTIVENESS EVALUATION ---\n")

    return {"effectiveness_score": score, "textual_feedback": feedback_text}

def save_results(post_content, validation, evaluation):
    """
    Saves the generated post, validation report, and feedback
    to JSON files with a timestamp and unique ID.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    unique_id = str(uuid.uuid4())[:8]

    # Data to save
    output_data = {
        "id": unique_id,
        "timestamp": timestamp,
        "generated_post": post_content,
        "validation_report": validation,
        "evaluation_feedback": evaluation
    }

    # Save the post and its report
    post_filename = f"post_{timestamp}_{unique_id}.json"
    with open(post_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print(f"Post and validation report saved to: {post_filename}")

    # Save the feedback for the next cycle
    feedback_filename = "feedback.json"
    with open(feedback_filename, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=4)
    print(f"Feedback for the next cycle saved to: {feedback_filename}")


# ==============================================================================
# CUSTOM TOOL DEFINITION
# ==============================================================================
class SimpleScraperTool(BaseTool):
    name: str = "Simple Website Scraper"
    description: str = "A simple tool to scrape the text content of a website given its URL."

    def _run(self, url: str) -> str:
        """Scrapes the text content of a website."""
        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text[:4000]
        except requests.exceptions.RequestException as e:
            return f"Error while scraping website {url}: {e}"


# ==============================================================================
# AGENT AND TASK DEFINITIONS
# ==============================================================================

def create_linkedin_crew(llm, feedback_context):
    """
    Creates and assembles the crew of agents with their tasks.
    This version uses a custom, reliable web scraper.
    """
    # Instantiate the custom tool
    web_scraper = SimpleScraperTool()

    # --- AGENT 1: Content Generator ---
    generator_agent = Agent(
        role="Expert in Responsible AI and the EU AI Act",
        goal="Create a high-quality, informative, and engaging weekly LinkedIn post focused on AI safety, ethics, and governance, aligned with the EU AI Act.",
        backstory=(
            "You are a renowned communications strategist with deep knowledge of the AI ecosystem, "
            "specializing in translating complex regulatory and technical concepts into clear, pragmatic content for an enterprise audience. "
            "Your style is visionary yet concrete, similar to Satya Nadella, inspiring trust and driving action."
        ),
        llm=llm,
        tools=[web_scraper],
        verbose=True,
        allow_delegation=False
    )

    # --- TASK: Post Generation ---
    generation_task = Task(
        description=f"""
        Create a LinkedIn post by strictly following these directives:

        1. **TOPIC**: Choose a specific theme related to Responsible AI, such as prompt injection, algorithmic transparency, data governance, or compliance with the EU AI Act.

        2. **SOURCES**: Use your web scraping tool to read the content from one or more of these authoritative sources. Your final post must be based on the information you find.
           - Official EU AI Act: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689
           - IEEE Ethics in AI: https://www.ieee.org/content/dam/ieee-org/ieee/web/org/about/initiatives/ieee-ethics-in-ai.pdf
           - MIT Technology Review (AI section): https://www.technologyreview.com/tag/artificial-intelligence/

        3. **POST STRUCTURE**:
           - **Catchy Title**: Max 10 words. Must be impactful (e.g., 'Secure AI: Beyond Compliance, Towards Trust').
           - **Introduction**: 3-4 sentences (40-60 words). Start with a provocative question or a bold statement to grab attention.
           - **Body**: 10-12 lines (120-180 words). Explain the chosen key concept. Include a practical example or a brief case study to make the content tangible.
           - **Conclusion**: 2-3 lines (20-40 words). End with a clear call-to-action and 1-2 relevant links from the sources.

        4. **STYLE AND LANGUAGE**:
           - **Tone**: Visionary and pragmatic. Inspire readers but also provide practical advice.
           - **Language**: Clear, direct, and accessible to a professional, non-technical audience. Avoid complex jargon.

        5. **FORMATTING**:
           - **Total Length**: Between 200 and 300 words.
           - **Mandatory Hashtags**: End the post EXACTLY with '#ResponsibleAI #EUAIAct'. Do not add other hashtags.

        6. **FEEDBACK TO CONSIDER**:
           {feedback_context}
        """,
        agent=generator_agent,
        expected_output="A complete LinkedIn post, formatted as plain text, ready to be copied and pasted. The post must adhere to ALL the provided directives, including length, structure, tone, and hashtags."
    )

    # Assemble the crew
    linkedin_crew = Crew(
        agents=[generator_agent],
        tasks=[generation_task],
        process=Process.sequential,
        verbose=2
    )

    return linkedin_crew

# ==============================================================================
# MAIN EXECUTION BLOCK
# ==============================================================================

if __name__ == "__main__":
    print("--- STARTING LINKEDIN POST CREATION PROCESS ---")

    # 1. Configure LLM
    llm = setup_llm()

    if llm:
        # 2. Load existing feedback
        # I'll rename the manual feedback file to be in English as well
        feedback_context = load_feedback(manual_feedback_file="manual_feedback.json")
        print("\n--- Feedback loaded for the generator ---")
        print(feedback_context)
        print("-----------------------------------------\n")

        # 3. Create and kick off the crew
        crew = create_linkedin_crew(llm, feedback_context)
        print("\n--- CrewAI is ready. Kicking off the generation task... ---\n")
        generated_post = crew.kickoff()

        print("\n\n--- GENERATION TASK COMPLETE ---")
        print("Post generated by the system:")
        print("--------------------------------------------------")
        print(generated_post)
        print("--------------------------------------------------")

        # 4. Validate the generated post
        validation_report = validate_post(generated_post)

        # 5. Evaluate effectiveness (with simulated data)
        mock_metrics = get_linkedin_metrics_mock(generated_post)
        evaluation_result = analyze_and_generate_feedback(mock_metrics)

        # 6. Save all results
        save_results(generated_post, validation_report, evaluation_result)

        print("\n--- PROCESS COMPLETE ---")
        print("Check the generated JSON files for full details.")

    else:
        print("Process aborted due to an LLM configuration error.")

# ==============================================================================
# SUGGESTIONS FOR FUTURE IMPROVEMENTS (as requested)
# ==============================================================================
# 1. Source Caching: To avoid re-downloading the same sources (e.g., the EU AI Act)
#    on every run, a caching system could be implemented. Before calling
#    `ScrapeWebsiteTool`, check if the content has been recently downloaded and
#    saved locally.
#
# 2. A/B Testing for Headlines: Modify the Generator Agent to create two or three
#    headline variations. Another task could then choose the best one based on
#    predictive engagement metrics (e.g., using a trained model).
#
# 3. Sentiment Analysis on Comments: In the real version with the LinkedIn API,
#    collect not just the number of comments but also their text. Use an NLP
#    library (e.g., NLTK, spaCy) to perform sentiment analysis. This would
#    provide much richer qualitative feedback (e.g., "The sentiment was negative,
#    perhaps the topic was too controversial").
#
# 4. Parallelization: If tasks were independent (e.g., generating posts for
#    different platforms), you could set `process=Process.parallel` in the Crew
#    to speed up execution. In this case, the process is inherently sequential.
#
# 5. Real LinkedIn API Integration: The `get_linkedin_metrics_mock` function
#    should be replaced with a class or module that handles the full OAuth 2.0
#    flow for authentication and calls to the real endpoints, with robust error
#    handling (rate limiting, expired tokens, etc.).
# ==============================================================================
