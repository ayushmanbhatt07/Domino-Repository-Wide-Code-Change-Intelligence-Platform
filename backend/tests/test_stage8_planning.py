import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from change_planning.models import ChangePlan

client = TestClient(app)

@pytest.fixture
def mock_planner_llm_service():
    mock_instance = MagicMock()
    
    mock_instance.generate_plan.return_value = ChangePlan(
        summary="Mock change plan",
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

def test_change_plan_endpoint(mock_planner_llm_service):
    payload = {
        "repo": "__test_fastapi",
        "request": "Replace SQLite with PostgreSQL",
        "target_entity": {
            "function_name": "get_db"
        }
    }
    
    with patch("impact_analysis.service.ImpactAnalysisService.analyze") as mock_analyze:
        mock_analyze.return_value = MagicMock(
            changed_entities=[{"id": "func1", "type": "Function", "name": "get_db"}],
            impacted=MagicMock(files=[], functions=[], classes=[], routes=[]),
            summary={"impacted_nodes": 0},
            truncated=False,
            warnings=[]
        )
        with patch("intelligence.hotspots.HotspotIdentifier.identify_hotspots") as mock_hotspots, \
             patch("intelligence.risk.RiskScorer.calculate_risk") as mock_risk, \
             patch("intelligence.test_recommender.TestRecommender.recommend") as mock_rec, \
             patch("change_planning.router.planning_service.llm_service", mock_planner_llm_service):
            
            mock_hotspots.return_value = []
            mock_risk.return_value = {"score": 50, "reasons": []}
            mock_rec.return_value = {"recommended_tests": [], "untested_impacted": []}
            
            response = client.post("/change/plan", json=payload)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["change_plan"]["summary"] == "Mock change plan"

def test_generate_patch_endpoint(mock_planner_llm_service):
    # Retrieve a valid model payload structure first
    plan = mock_planner_llm_service.generate_plan()
    
    payload = {
        "repo": "__test_fastapi",
        "change_request": "Do thing",
        "plan": plan.model_dump()
    }
    
    with patch("change_planning.router.planning_service.llm_service", mock_planner_llm_service):
        response = client.post("/change/patch", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert "--- a/auth/auth_database.py" in data["patch"]
        assert data["validation"]["valid"] == True
        assert data["validation"]["scope_status"] == "valid"

def test_patch_validation():
    payload = {
        "repo": "__test_fastapi",
        "patch": "--- a/secret/.env\n+++ b/secret/.env\n@@ -1,1 +1,1 @@\n-old\n+new",
        "plan": None
    }
    response = client.post("/change/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == False
    assert data["security_status"] == "invalid"
    assert "Modification of potential secrets is not allowed" in data["warnings"][0]
