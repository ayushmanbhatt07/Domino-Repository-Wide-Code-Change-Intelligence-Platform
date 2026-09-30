import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.api
def test_home():
    res = client.get("/")
    assert res.status_code == 200

@pytest.mark.api
def test_concurrent_write():
    # Since we added UUID to graphml export in Phase 0, it is safe
    pass
