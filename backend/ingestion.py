import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

import requests
from git import Repo, GitCommandError


class RepositoryIngestionService:
    def __init__(self):
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)

    def validate_url(self, repo_url: str) -> bool:
        if not repo_url or not isinstance(repo_url, str):
            return False
            
        # Clean URL
        repo_url = repo_url.strip()
        parsed = urlparse(repo_url)

        if parsed.scheme not in ("http", "https"):
            return False

        if parsed.netloc != "github.com":
            return False

        path = parsed.path.strip("/").split("/")
        if len(path) < 2:
            return False

        return True

    def repository_exists(self, repo_url: str) -> bool:
        # Just head request to see if it's there
        # For ".git" suffix remove it for web request
        clean_url = repo_url
        if clean_url.endswith(".git"):
            clean_url = clean_url[:-4]
        try:
            response = requests.head(clean_url, allow_redirects=True, timeout=5)
            return response.status_code == 200
        except:
            return False

    def ingest(self, repo_url: str, custom_repo_name: str = None):
        if not self.validate_url(repo_url):
            raise ValueError("Invalid GitHub Repository URL.")

        if not self.repository_exists(repo_url):
            raise ValueError("Repository does not exist or is inaccessible.")

        parsed = urlparse(repo_url.strip())
        path_parts = parsed.path.strip("/").split("/")
        owner = path_parts[0]
        name = path_parts[1]
        if name.endswith(".git"):
            name = name[:-4]
            
        repo_id = custom_repo_name or f"{owner}__{name}"
        
        import uuid
        folder_name = f"{repo_id}_{uuid.uuid4().hex[:8]}"
        clone_path = self.workspace / folder_name

        try:
            repo = Repo.clone_from(repo_url, clone_path, depth=1)
            commit_sha = repo.head.commit.hexsha
            
            return {
                "repository": repo_id,
                "path": str(clone_path),
                "commit_sha": commit_sha
            }
        except GitCommandError as e:
            raise RuntimeError(f"Git Clone Failed : {e}")
            
    def cleanup(self, path: str):
        if path and os.path.exists(path) and "workspace" in path:
            try:
                # Handle Windows permissions issues with .git folder
                import stat
                def remove_readonly(func, path, excinfo):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                shutil.rmtree(path, onerror=remove_readonly)
            except Exception as e:
                pass # Best effort