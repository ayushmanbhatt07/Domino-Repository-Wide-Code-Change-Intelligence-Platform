import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from ai_reasoning.models import AIExplanation, ReasonResponse

client = TestClient(app)

@pytest.fixture
def mock_llm_service():
    mock_instance = MagicMock()
    mock_instance.generate_reasoning.return_value = AIExplanation(
        summary="Mock summary",
        impact_explanation="Mock impact",
        risk_explanation="Mock risk",
        affected_components=["mock_component"],
        testing_guidance="Mock testing",
        change_considerations="Mock considerations",
        evidence=[],
        limitations=["Mock limitation"]
    )
    return mock_instance

@pytest.mark.asyncio
async def test_reason_endpoint(mock_llm_service):
    payload = {
        "repo": "__test_fastapi",
        "target": {
            "function_name": "get_db"
        },
        "question": "What happens if I change this?"
    }
    
    with patch("impact_analysis.service.ImpactAnalysisService.analyze") as mock_analyze:
        mock_analyze.return_value = MagicMock(
            changed_entities=[{"id": "func1", "type": "Function", "name": "get_db", "file": "main.py"}],
            impacted=MagicMock(files=[], functions=[], classes=[], routes=[]),
            summary={"impacted_nodes": 0},
            truncated=False,
            warnings=[]
        )
        with patch("intelligence.hotspots.HotspotIdentifier.identify_hotspots") as mock_hotspots, \
             patch("intelligence.risk.RiskScorer.calculate_risk") as mock_risk, \
             patch("intelligence.test_recommender.TestRecommender.recommend") as mock_rec:
            
            mock_hotspots.return_value = []
            mock_risk.return_value = {"score": 50, "reasons": ["Risk reason"]}
            mock_rec.return_value = {"recommended_tests": [], "untested_impacted": []}
            
            with patch("ai_reasoning.router.reasoning_service.llm_service", mock_llm_service):
                response = client.post("/reason", json=payload)
                assert response.status_code == 200
                data = response.json()
            
            assert "ai_reasoning" in data
            assert data["ai_reasoning"]["summary"] == "Mock summary"
            assert data["risk_summary"]["score"] == 50
