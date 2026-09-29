import networkx as nx

class TestRecommender:
    def __init__(self, metrics_cache):
        self.cache = metrics_cache
        
    def recommend(self, repo: str, impacted_ids: list[str]) -> dict:
        g = self.cache.get_graph(repo)
        
        test_nodes = [n for n, d in g.nodes(data=True) if d.get("is_test")]
        
        covered_by = {} # node_id -> list of test_ids
        for n in impacted_ids:
            covered_by[n] = []
            
        # To find shortest path from any test to any impacted node,
        # we can just do a BFS from test nodes or BFS upstream from impacted nodes.
        # NetworkX has multi-source shortest path
        
        # We need shortest path FROM test TO impacted node.
        # So we can use reverse graph and do multi-source shortest path from impacted nodes
        rg = g.reverse(copy=False)
        
        recommended_tests = {} # test_id -> min_distance
        
        for imp in impacted_ids:
            if imp not in rg: continue
            
            # BFS from imp
            lengths = nx.single_source_shortest_path_length(rg, imp, cutoff=5) # reasonable limit
            found_test = False
            for node, dist in lengths.items():
                if g.nodes[node].get("is_test"):
                    found_test = True
                    covered_by[imp].append(node)
                    if node not in recommended_tests or dist < recommended_tests[node]:
                        recommended_tests[node] = dist
            
        untested = [n for n, tests in covered_by.items() if not tests]
        
        # Rank tests by min distance
        sorted_tests = sorted(recommended_tests.items(), key=lambda x: x[1])
        test_list = []
        for t, d in sorted_tests:
            tdata = g.nodes[t]
            test_list.append({
                "id": t,
                "name": tdata.get("name"),
                "file": tdata.get("path"),
                "distance": d
            })
            
        return {
            "recommended_tests": test_list,
            "untested_impacted": untested
        }
