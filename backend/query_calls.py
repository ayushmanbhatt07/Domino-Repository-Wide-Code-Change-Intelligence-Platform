import sys
from neo4j import GraphDatabase
import config
driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=None)
with driver.session(database=config.NEO4J_DATABASE) as s:
    print("\nCalls:")
    res = list(s.run("MATCH (f1 {repo: 'ayushmanbhatt07__fastapi_tutorial'})-[r:CALLS]->(f2) RETURN f1.name, f2.name, r.resolution, r.confidence LIMIT 20"))
    for r in res:
        print(f"{r['f1.name']} -> {r['f2.name']} ({r['r.resolution']}, {r['r.confidence']})")
    
    print("\nFunctions with Same Name Calls:")
    res = list(s.run("MATCH (f1 {repo: 'ayushmanbhatt07__fastapi_tutorial'})-[r:CALLS]->(f2) WHERE f2.name='create' RETURN f1.name, f2.name, f2.id LIMIT 10"))
    for r in res:
        print(f"{r['f1.name']} -> {r['f2.name']} (id: {r['f2.id']})")
