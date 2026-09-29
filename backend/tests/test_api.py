import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.api
def test_home():
    res = client.get("/")
    assert res.status_code == 200

@pytest.mark.api
@pytest.mark.xfail(strict=True, reason="fixed graphs/{repo_name}.graphml path is unsafe (B10)")
def test_concurrent_write():
    # If we call analyze twice concurrently, it overwrites the same file
    assert False, "Unsafe concurrent write to fixed .graphml path"
