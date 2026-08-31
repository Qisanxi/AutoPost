"""
ADK tool tests.
"""

import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app import main as main_module
from app.agents.tools.discovery_tools import search_github_trending, fetch_repo_readme
from app.agents.tools.generation_tools import generate_content_for_platform
from app.agents.tools.memory_tools import save_repo_to_firestore


class TestDiscoveryTools:
    @patch("app.agents.tools.discovery_tools.GitHubClient")
    def test_search_github_trending(self, mock_client):
        mock_instance = MagicMock()
        mock_instance.search_trending.return_value = [
            {"url": "https://github.com/test/repo", "name": "repo", "stars": 100}
        ]
        mock_client.return_value = mock_instance

        result = search_github_trending(language="python", limit=1)
        assert len(result) == 1
        assert result[0]["name"] == "repo"

    @patch("app.main.GitHubClient")
    @patch("app.main.FirestoreClient")
    def test_discover_repos_includes_metrics(self, mock_firestore_client, mock_github_client):
        mock_github = MagicMock()
        mock_github.search_trending.return_value = [
            {"url": "https://github.com/test/repo-1", "name": "repo1", "stars": 11, "topics": ["python"], "description": "Alpha", "readme_url": "https://raw.githubusercontent.com/test/repo-1/main/README.md"},
            {"url": "https://github.com/test/repo-2", "name": "repo2", "stars": 9, "topics": ["python"], "description": "Beta", "readme_url": "https://raw.githubusercontent.com/test/repo-2/main/README.md"},
        ]
        mock_github_client.return_value = mock_github

        firestore_instance = MagicMock()
        firestore_instance.check_duplicate.side_effect = [False, True]
        firestore_instance.create_repo.return_value = "doc-1"
        mock_firestore_client.return_value = firestore_instance

        original_db = main_module.db
        main_module.db = MagicMock()
        try:
            client = TestClient(main_module.app)
            response = client.post("/agent/discover", params={"languages": "python", "limit": 5})
            assert response.status_code == 200
            payload = response.json()
            assert payload["github_found"] == 2
            assert payload["duplicates_skipped"] == 1
            assert payload["count"] == 1
            assert payload["repos"][0]["name"] == "repo1"
        finally:
            main_module.db = original_db

    @patch("app.agents.tools.discovery_tools.GitHubClient")
    def test_fetch_repo_readme(self, mock_client):
        mock_instance = MagicMock()
        mock_instance.fetch_readme.return_value = "# README\nThis is a test."
        mock_client.return_value = mock_instance

        result = fetch_repo_readme("https://github.com/test/repo")
        assert "README" in result

    def test_fetch_repo_readme_invalid_url(self):
        result = fetch_repo_readme("https://evil.com/repo")
        assert "Error" in result


class TestGenerationTools:
    @patch("app.agents.tools.generation_tools.get_genai_client")
    def test_generate_linkedin(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "This is a LinkedIn post about AI agents."
        mock_client.models.generate_content.return_value = mock_response

        analysis = json.dumps({
            "raw_name": "test-repo",
            "problem_solved": "Testing",
            "tech_stack": ["Python"],
            "one_liner_hook": "Test hook",
        })
        result = generate_content_for_platform(analysis, "linkedin")
        assert result["success"] is True
        assert result["platform"] == "linkedin"

    @patch("app.agents.tools.generation_tools.get_genai_client")
    def test_generate_devto(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "# Title\n\nThis is an article."
        mock_client.models.generate_content.return_value = mock_response

        analysis = json.dumps({
            "raw_name": "test-repo",
            "problem_solved": "Testing",
            "tech_stack": ["Python"],
            "target_audience": "Developers",
            "key_files": ["main.py"],
        })
        result = generate_content_for_platform(analysis, "devto")
        assert result["success"] is True
        assert "devto" in result["platform"]
        assert "title" in result

    def test_invalid_platform(self):
        result = generate_content_for_platform("{}", "twitter")
        assert "error" in result


class TestMemoryTools:
    @patch("app.agents.tools.memory_tools.get_db_client")
    def test_save_repo(self, mock_get_db_client):
        mock_client = MagicMock()
        mock_client.create_repo.return_value = "test-doc-123"
        mock_get_db_client.return_value = mock_client

        repo_data = json.dumps({
            "github_url": "https://github.com/test/repo",
            "status": "pending_analysis",
        })
        result = save_repo_to_firestore(repo_data)
        assert result["success"] is True
        assert result["document_id"] == "test-doc-123"