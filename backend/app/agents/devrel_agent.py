"""
DevRel Agent — Google ADK Agent Definition
Wires all tools into a reasoning loop. This is the "brain" of the system.
"""

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import Session

from .tools.discovery_tools import search_github_trending, fetch_repo_readme, fetch_hacker_news_show_hn
from .tools.analysis_tools import analyze_repository, generate_linkedin_post, generate_devto_article
from .tools.generation_tools import generate_content_for_platform
from .tools.publishing_tools import publish_to_linkedin, publish_to_devto, send_discord_notification, send_discord_embed
from .tools.memory_tools import save_repo_to_firestore, save_post_to_firestore, get_recent_repos

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM INSTRUCTION — The Agent's "Personality"
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """You are a DevRel Content Agent. Your goal is to find interesting GitHub repositories and publish professional posts about them.

WORKFLOW:
1. DISCOVER: Call search_github_trending() to find repos.
2. DEDUPLICATE: For each repo, check if already in Firestore via get_recent_repos().
3. ANALYZE: Call fetch_repo_readme() then analyze_repository().
4. CURATE: If novelty_score < 7.5, skip. Otherwise approve.
5. GENERATE: Call generate_content_for_platform() for LinkedIn and Dev.to.
6. PUBLISH: Call publish_to_linkedin() and publish_to_devto().
7. NOTIFY: Call send_discord_notification() to report results.
8. SAVE: Call save_repo_to_firestore() and save_post_to_firestore() after each step.

RULES:
- Always check for duplicates before analyzing.
- Never publish without generating content first.
- If publishing fails, retry once. If it fails again, log error and move on.
- If no repos score above 7.5, report "No high-quality repos found today."
- Be concise in your reasoning. Focus on action.
- Do not hallucinate repository details. Only use data from the README and metadata.
- Respect the daily post limit. Do not queue more than 3 posts per run.
- When generating content, tailor tone per platform:
  * LinkedIn: Professional, conversational, 3-4 paragraphs, end with question
  * Dev.to: Technical, markdown, 800-1200 words, include code snippets if relevant
"""

# ─────────────────────────────────────────────────────────────────────────────
# AGENT DEFINITION
# ─────────────────────────────────────────────────────────────────────────────

devrel_agent = Agent(
    model="gemini-3.5-flash",
    name="devrel_content_agent",
    description="Autonomous agent that discovers, analyzes, and publishes dev content",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        # Discovery
        search_github_trending,
        fetch_repo_readme,
        fetch_hacker_news_show_hn,
        # Analysis
        analyze_repository,
        # Generation
        generate_linkedin_post,
        generate_devto_article,
        generate_content_for_platform,
        # Publishing
        publish_to_linkedin,
        publish_to_devto,
        send_discord_notification,
        send_discord_embed,
        # Memory
        save_repo_to_firestore,
        save_post_to_firestore,
        get_recent_repos,
    ],
)

# ─────────────────────────────────────────────────────────────────────────────
# RUNNER — Execute the agent
# ─────────────────────────────────────────────────────────────────────────────

def run_agent_session(query: str = "Run the daily content discovery and publishing workflow.") -> dict:
    """
    Execute one agent session.
    Returns the final response and tool call history.
    """
    session = Session()
    runner = Runner(agent=devrel_agent, session=session)

    response = runner.run(query=query)

    return {
        "final_response": response,
        "session_id": session.id,
        "tool_calls": session.tool_calls if hasattr(session, "tool_calls") else [],
    }