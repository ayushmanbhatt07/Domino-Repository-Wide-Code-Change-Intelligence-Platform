import pytest
from analysis import RepositoryAnalyzer
from dependency_graph import DependencyGraphBuilder

@pytest.fixture
def graph():
    a = RepositoryAnalyzer()
    res = a.analyze("d:/Domino-Repository-Wide-Code-Change-Intelligence-Platform/backend/tests/fixtures/sample_repo")
    b = DependencyGraphBuilder()
    return b.build(res)

@pytest.mark.stage3
def test_function_collisions(graph):
    # Two create methods should have different nodes, e.g. function:app/services/user_service.py:UserService.create
    nodes = [n for n in graph.nodes()]
    # Path will use forward slashes. Need to make sure the qualified name is correct.
    assert any("UserService.create" in n for n in nodes)

@pytest.mark.stage3
def test_call_resolution(graph):
    edges = graph.edges(data=True)
    # create() calls validate_user() which should resolve internally
    calls = [v for u, v, data in edges if data["relation"] == "calls" and "create" in u]
    assert any("validate_user" in v for v in calls)

@pytest.mark.stage3
def test_imports_edges(graph):
    edges = graph.edges(data=True)
    imports = [data for u, v, data in edges if data.get("relation") == "imports"]
    assert len(imports) > 0
    
@pytest.mark.stage3
def test_handled_by_edges(graph):
    edges = graph.edges(data=True)
    # Route handles
    handled_by = [v for u, v, data in edges if data["relation"] == "handled_by" and "route:" in u]
    assert len(handled_by) > 0
