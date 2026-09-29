from graph_store import Neo4jGraphStore
from impact_analysis.matcher import ImpactMatcher
from impact_analysis.traversal import ImpactTraversal
import traceback
import sys

def main():
    print("Testing Neo4j connection...")
    try:
        store = Neo4jGraphStore()
        # Test connection
        with store.driver.session() as session:
            result = session.run("MATCH (n) RETURN COUNT(n) AS count")
            count = result.single()["count"]
            print(f"Neo4j connection successful! Total nodes in DB: {count}")
            
            print("\nRepositories in DB:")
            result = session.run("MATCH (n) RETURN DISTINCT n.repo AS repo")
            repos = [r["repo"] for r in result if r["repo"]]
            for r in repos:
                print(f" - {r}")
                
            if repos:
                print(f"\nCounting nodes by label for repo '{repos[0]}':")
                result = session.run("MATCH (n {repo: $repo}) RETURN labels(n) AS labels, count(n) AS count", repo=repos[0])
                for r in result:
                    print(f" - {r['labels']}: {r['count']}")
                    
                print(f"\nSample Function nodes for repo '{repos[0]}':")
                result = session.run("MATCH (f:Function {repo: $repo}) RETURN f.name AS name, f.id AS id LIMIT 3", repo=repos[0])
                for r in result:
                    print(f" - {r['name']} ({r['id']})")
                    
                # Test Matcher & Traversal on real DB
                print("\nTesting Matcher on real DB...")
                matcher = ImpactMatcher(store)
                traversal = ImpactTraversal(store)
                
                # find a function to test
                result = session.run("MATCH (f:Function {repo: $repo}) RETURN f.name AS name LIMIT 1", repo=repos[0])
                func_name = result.single()["name"]
                print(f"Matching function: {func_name}")
                entity = matcher.match(repo=repos[0], function_name=func_name)
                print(f"Matched Entity: {entity}")
                
                print(f"\nTraversing downstream for {entity['id']}...")
                downstream_nodes = traversal.downstream(repo=repos[0], node_id=entity["id"], depth=3)
                for node in downstream_nodes:
                    print(f" - {node}")
        
    except Exception as e:
        print("Neo4j connection failed or unreachable:")
        print(traceback.format_exc())
    finally:
        try:
            store.close()
        except:
            pass

if __name__ == '__main__':
    main()
