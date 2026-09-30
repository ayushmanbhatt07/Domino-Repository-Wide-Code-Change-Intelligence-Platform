import pytest
import config
import inspect

@pytest.mark.stage4
@pytest.mark.neo4j
def test_save_graph(neo4j_store):
    from analysis import RepositoryAnalyzer
    from dependency_graph import DependencyGraphBuilder
    
    a = RepositoryAnalyzer()
    res = a.analyze("d:/Domino-Repository-Wide-Code-Change-Intelligence-Platform/backend/tests/fixtures/sample_repo")
    b = DependencyGraphBuilder()
    g = b.build(res)
    
    neo4j_store.save("__test_fixture", g)
    
    with neo4j_store.driver.session(database=config.NEO4J_DATABASE) as session:
        count = session.run("MATCH (n {repo: '__test_fixture'}) RETURN count(n) as c").single()["c"]
        assert count > 0

@pytest.mark.stage4
def test_batching(neo4j_store):
    source = inspect.getsource(neo4j_store._replace_repo_tx)
    assert "UNWIND" in source

@pytest.mark.stage4
def test_uniqueness_constraints(neo4j_store):
    neo4j_store.ensure_schema()
    with neo4j_store.driver.session(database=config.NEO4J_DATABASE) as session:
        constraints = list(session.run("SHOW CONSTRAINTS"))
        assert any("id" in str(c) for c in constraints)
