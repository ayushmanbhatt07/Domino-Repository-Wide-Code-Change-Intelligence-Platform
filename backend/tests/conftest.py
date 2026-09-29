import pytest
from neo4j import GraphDatabase
import config
from graph_store import Neo4jGraphStore

@pytest.fixture(scope="session")
def neo4j_store():
    store = Neo4jGraphStore()
    yield store
    store.close()

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_repos(neo4j_store):
    yield
    with neo4j_store.driver.session(database=config.NEO4J_DATABASE) as session:
        session.run("MATCH (n) WHERE n.repo STARTS WITH '__test_' DETACH DELETE n")
