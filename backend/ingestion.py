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
        clean_url = repo_url
        if clean_url.endswith(".git"):
            clean_url = clean_url[:-4]
        try:
            response = requests.head(clean_url, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass

        # Fallback to git ls-remote (supports private/credential-authenticated repos)
        try:
            from git import cmd
            g = cmd.Git()
            output = g.ls_remote(repo_url)
            return bool(output)
        except Exception:
            return False

    def ingest(self, repo_url: str, custom_repo_name: str = None, ref: str = None):
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
            repo = self._clone(repo_url, clone_path, ref)
            commit_sha = repo.head.commit.hexsha
            repo.close()  # Release file handles to prevent lock on Windows
            
            return {
                "repository": repo_id,
                "path": str(clone_path),
                "commit_sha": commit_sha
            }
        except GitCommandError as e:
            raise RuntimeError(f"Git Clone Failed : {e}")
            
    def _clone(self, repo_url: str, clone_path, ref: str = None):
        """Clone the default branch, or the given branch/tag/commit when ref is set."""
        ref = (ref or "").strip()
        if not ref or ref == "unknown":
            return Repo.clone_from(repo_url, clone_path, depth=1)
        try:
            return Repo.clone_from(repo_url, clone_path, depth=1, branch=ref)
        except GitCommandError:
            # ref may be a commit SHA (or a default branch name that doesn't exist)
            self.cleanup(str(clone_path))
            repo = Repo.clone_from(repo_url, clone_path)
            try:
                repo.git.checkout(ref)
            except GitCommandError:
                repo.close()
                self.cleanup(str(clone_path))
                raise RuntimeError(f"Branch or commit '{ref}' not found in repository.")
            return repo

    def cleanup(self, path: str):
        if path and os.path.exists(path) and "workspace" in path:
            import stat
            for root, dirs, files in os.walk(path):
                for dir in dirs:
                    os.chmod(os.path.join(root, dir), stat.S_IWRITE)
                for file in files:
                    os.chmod(os.path.join(root, file), stat.S_IWRITE)
            try:
                shutil.rmtree(path)
            except Exception:
                pass # Best effort