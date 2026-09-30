import sys
sys.path.insert(0, '.')
from graph_store import Neo4jGraphStore
import config
store = Neo4jGraphStore()
with store.driver.session(database=config.NEO4J_DATABASE) as s:
    res = list(s.run("MATCH (n {repo: 'ayushmanbhatt07__fastapi_tutorial'}) RETURN labels(n) as lbl, count(n) as c"))
    for r in res:
        print(f"{r['lbl']}: {r['c']}")
    
    print("\nRelationships:")
    res = list(s.run("MATCH ()-[r]->() WHERE r.repo='ayushmanbhatt07__fastapi_tutorial' OR type(r) IS NOT NULL RETURN type(r) as t, count(r) as c"))
    for r in res:
        print(f"{r['t']}: {r['c']}")

    print("\nFiles:")
    res = list(s.run("MATCH (f:File {repo: 'ayushmanbhatt07__fastapi_tutorial'}) RETURN f.id LIMIT 10"))
    for r in res:
        print(r['f.id'])

    print("\nRoutes:")
    res = list(s.run("MATCH (r:Route {repo: 'ayushmanbhatt07__fastapi_tutorial'}) RETURN r.id"))
    for r in res:
        print(r['r.id'])
