import pytest
from impact_analysis.matcher import ImpactMatcher
from impact_analysis.traversal import ImpactTraversal
from impact_analysis.models import EntitySelector

@pytest.mark.stage5
def test_matcher_missing(neo4j_store):
    matcher = ImpactMatcher(neo4j_store)
    res = matcher.match("__test_fixture", EntitySelector(function_name="nonexistent"))
    assert res["status"] == "NOT_FOUND"

@pytest.mark.stage5
def test_traversal_direction(neo4j_store):
    traversal = ImpactTraversal(neo4j_store)
    # Using the exact seeds logic
    # We just ensure it runs without error, the graph might be empty but it won't crash
    res, trunc = traversal.upstream_impact("__test_fixture", ["some_id"])
    assert isinstance(res, list)

@pytest.mark.stage5
def test_service_exists():
    import impact_analysis.service
