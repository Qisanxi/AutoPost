"""
Google ADK Publishing Tools — post to LinkedIn, Dev.to, Discord.
"""

from typing import Dict, Any

from google.adk.tools import tool

from ...services.linkedin_client import LinkedInClient
from ...services.devto_client import DevToClient
from ...services.discord_client import DiscordClient
from ...exceptions import PublishingError


@tool
def publish_to_linkedin(content: str) -> Dict[str, Any]:
    """
    Publish a post to your personal LinkedIn profile.
    Content should be professional, include insights, and end with a question.
    """
    client = LinkedInClient()
    return client.publish_post(content)


@tool
def publish_to_devto(title: str, body: str, tags: list) -> Dict[str, Any]:
    """
    Publish a technical article to Dev.to.
    Title should be SEO-friendly. Body should be markdown formatted.
    Tags should be 1-4 relevant tech topics.
    """
    client = DevToClient()
    return client.publish_article(title, body, tags)


@tool
def send_discord_notification(message: str) -> Dict[str, Any]:
    """
    Send a notification to the Discord webhook.
    Use this to report agent activity, errors, or completed posts.
    """
    client = DiscordClient()
    return client.send_notification(message)


@tool
def send_discord_embed(title: str, description: str, url: str = "") -> Dict[str, Any]:
    """
    Send a rich embed notification to Discord.
    Use for completed posts with links.
    """
    client = DiscordClient()
    return client.send_embed(title, description, url=url)