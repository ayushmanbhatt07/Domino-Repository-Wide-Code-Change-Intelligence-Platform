import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock
from ai_reasoning.models import AIExplanation

client = TestClient(app)

@pytest.fixture
def mock_llm_service():
    mock_instance = MagicMock()
    mock_instance.generate_reasoning.return_value = AIExplanation(
        summary="Mock summary",
        impact_explanation="Mock impact",
        risk_explanation="Mock risk",
        affected_components=["route:POST:/books", "function:project.py:create_book"],
        testing_guidance="Mock testing",
        change_considerations="Mock considerations",
        evidence=[],
        limitations=["Mock limitation"]
    )
    return mock_instance

def test_e2e_reasoning(mock_llm_service):
    repo_name = "ayushmanbhatt07__fastapi_tutorial"
    
    # Send reason request for get_db
    payload = {
        "repo": repo_name,
        "target": {
            "function_name": "get_db",
            "file_name": "auth/auth_database.py"
        },
        "question": "Why is this function critical?"
    }
    
    with patch("ai_reasoning.router.reasoning_service.llm_service", mock_llm_service):
        response = client.post("/reason", json=payload)
        
    assert response.status_code == 200, response.text
    data = response.json()
    
    # Verify deterministic fields
    assert "target" in data
    assert data["target"]["name"] == "get_db"
    assert "auth_database.py" in data["target"]["id"]
    
    # Impact summary
    assert "impact_summary" in data
    assert data["impact_summary"]["impacted_functions"] > 0
    
    # Risk
    assert "risk_summary" in data
    assert data["risk_summary"]["score"] > 0
    
    # AI Reasoning
    assert "ai_reasoning" in data
    assert data["ai_reasoning"]["summary"] == "Mock summary"
    assert "route:POST:/books" in data["ai_reasoning"]["affected_components"]
