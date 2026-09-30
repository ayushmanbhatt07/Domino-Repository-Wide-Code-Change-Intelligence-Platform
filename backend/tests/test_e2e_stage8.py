import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock
from change_planning.models import ChangePlan

client = TestClient(app)

@pytest.fixture
def mock_planner_llm_service():
    mock_instance = MagicMock()
    mock_instance.generate_plan.return_value = ChangePlan(
        summary="Mock summary",
        requested_change="Replace SQLite with PostgreSQL",
        affected_files=[{"path": "auth/auth_database.py", "reason": "Uses DB", "source": "graph_verified", "confidence": "High"}],
        affected_functions=[],
        affected_classes=[],
        affected_routes=[],
        implementation_steps=[{"step_number": 1, "description": "Update get_db", "target_file": "auth/auth_database.py", "target_symbol": "get_db"}],
        dependency_changes=["psycopg2"],
        configuration_changes=["DATABASE_URL"],
        database_changes=["Use postgresql://"],
        api_changes=[],
        test_changes=[],
        potential_breaking_changes=[],
        risk_considerations=[],
        assumptions=[],
        evidence=[],
        validation_steps=[{"step_number": 1, "description": "Run tests"}],
        confidence="High",
        limitations=[]
    )
    
    mock_instance.generate_patch.return_value = "--- a/auth/auth_database.py\n+++ b/auth/auth_database.py\n@@ -1,1 +1,1 @@\n-old\n+new"
    
    return mock_instance

def test_e2e_change_planning(mock_planner_llm_service):
    repo_name = "ayushmanbhatt07__fastapi_tutorial"
    
    # 1. Plan change
    plan_payload = {
        "repo": repo_name,
        "request": "Replace SQLite with PostgreSQL",
        "target_entity": {
            "function_name": "get_db",
            "file_name": "auth/auth_database.py"
        }
    }
    
    with patch("change_planning.router.planning_service.llm_service", mock_planner_llm_service):
        plan_response = client.post("/change/plan", json=plan_payload)
        
    assert plan_response.status_code == 200, plan_response.text
    plan_data = plan_response.json()
    
    assert "change_plan" in plan_data
    assert plan_data["impact"]["impacted_functions"] > 0
    assert plan_data["risk"]["score"] > 0
    
    plan = plan_data["change_plan"]
    
    # 2. Generate patch
    patch_payload = {
        "repo": repo_name,
        "change_request": "Replace SQLite with PostgreSQL",
        "plan": plan
    }
    
    with patch("change_planning.router.planning_service.llm_service", mock_planner_llm_service):
        patch_response = client.post("/change/patch", json=patch_payload)
        
    assert patch_response.status_code == 200, patch_response.text
    patch_data = patch_response.json()
    
    assert "patch" in patch_data
    assert "auth/auth_database.py" in patch_data["files_changed"]
    
    validation = patch_data["validation"]
    assert validation["valid"] == True
    assert validation["scope_status"] == "valid"
    assert validation["security_status"] == "valid"
