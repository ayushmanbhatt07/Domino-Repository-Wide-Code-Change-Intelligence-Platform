import pytest
from ingestion import RepositoryIngestionService
import os

@pytest.fixture
def service():
    return RepositoryIngestionService()

@pytest.mark.stage1
def test_valid_github_url(service):
    res = service.ingest("https://github.com/ayushmanbhatt07/Domino-Repository-Wide-Code-Change-Intelligence-Platform")
    assert "repository" in res
    assert "path" in res
    assert os.path.exists(res["path"])

@pytest.mark.stage1
def test_url_variants(service):
    assert service.validate_url("https://github.com/owner/repo/")
    assert service.validate_url("http://github.com/owner/repo.git")
    assert service.validate_url("https://github.com/OWNER/REPO")

@pytest.mark.stage1
def test_invalid_urls(service):
    assert not service.validate_url("")
    assert not service.validate_url(None)
    assert not service.validate_url("not-a-url")
    assert not service.validate_url("https://gitlab.com/owner/repo")
    
@pytest.mark.stage1
@pytest.mark.xfail(strict=True, reason="workspace/ clones never cleaned up (B9)")
def test_cleanup(service):
    before = len(os.listdir(service.workspace))
    try:
        service.ingest("https://github.com/ayushmanbhatt07/Domino-Repository-Wide-Code-Change-Intelligence-Platform")
    except:
        pass
    after = len(os.listdir(service.workspace))
    assert after == before
