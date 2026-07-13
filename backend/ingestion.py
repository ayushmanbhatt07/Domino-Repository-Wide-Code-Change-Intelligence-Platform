from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

import requests
from git import Repo, GitCommandError


class RepositoryIngestionService:
    """
    Handles:
    1. URL Validation
    2. Repository Existence Check
    3. Repository Cloning
    """

    def __init__(self):
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)

    # -----------------------------
    # Validate URL
    # -----------------------------
    def validate_url(self, repo_url: str) -> bool:

        parsed = urlparse(repo_url)

        if parsed.scheme not in ("http", "https"):
            return False

        if parsed.netloc != "github.com":
            return False

        path = parsed.path.strip("/").split("/")

        if len(path) < 2:
            return False

        return True

    # -----------------------------
    # Check Repository Exists
    # -----------------------------
    def repository_exists(self, repo_url: str) -> bool:

        response = requests.get(repo_url)

        return response.status_code == 200

    # -----------------------------
    # Clone Repository
    # -----------------------------
    def clone_repository(self, repo_url: str):

        repo_name = repo_url.rstrip("/").split("/")[-1]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        folder_name = f"{repo_name}_{timestamp}"

        clone_path = self.workspace / folder_name

        Repo.clone_from(repo_url, clone_path)

        return {
            "repository": repo_name,
            "path": str(clone_path)
        }

    # -----------------------------
    # Main Pipeline
    # -----------------------------
    def ingest(self, repo_url: str):

        if not self.validate_url(repo_url):
            raise ValueError("Invalid GitHub Repository URL.")

        if not self.repository_exists(repo_url):
            raise ValueError("Repository does not exist or is inaccessible.")

        try:

            result = self.clone_repository(repo_url)

            return result

        except GitCommandError as e:

            raise RuntimeError(f"Git Clone Failed : {e}")