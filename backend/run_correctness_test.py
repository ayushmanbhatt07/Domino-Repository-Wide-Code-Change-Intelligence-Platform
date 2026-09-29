import sys
import json
from analysis import RepositoryAnalyzer
from dependency_graph import DependencyGraphBuilder

def main():
    analyzer = RepositoryAnalyzer()
    analysis = analyzer.analyze("d:/Domino-Repository-Wide-Code-Change-Intelligence-Platform/backend")
    
    builder = DependencyGraphBuilder()
    graph = builder.build(analysis)
    
    # print summary
    print("Graph Summary:")
    print(builder.summary())
    
    # print node types
    node_types = {}
    for _, data in graph.nodes(data=True):
        t = data.get("type", "unknown")
        node_types[t] = node_types.get(t, 0) + 1
    print("\nNode Types:", node_types)
    
    # print edge types
    edge_types = {}
    for _, _, data in graph.edges(data=True):
        t = data.get("relation", "unknown")
        edge_types[t] = edge_types.get(t, 0) + 1
    print("Edge Types:", edge_types)

    # find a function that is called by at least one other function
    in_degrees = {}
    for u, v, data in graph.edges(data=True):
        if data.get("relation") == "calls":
            in_degrees[v] = in_degrees.get(v, []) + [u]
            
    test_func = None
    for target, callers in in_degrees.items():
        if graph.nodes[target].get("type") == "function" and len(callers) > 0:
            test_func = target
            break
            
    if test_func:
        print(f"\nCorrectness Test: Target Function = {test_func}")
        print(f"Correct Impacted Set (Callers that depend on this function, meaning if {test_func} changes, these are impacted):")
        for c in in_degrees[test_func]:
            print(f" - {c}")
            
        print("\nActual Traversal Output (using downstream logic from traversal.py which follows OUTGOING edges):")
        # simulate traversal.downstream which does (start)-[*1..3]->(n)
        # meaning what does this function depend on?
        import networkx as nx
        downstream = list(nx.bfs_tree(graph, test_func, depth_limit=3))
        # bfs_tree includes the root, so slice
        for n in downstream[1:]:
            print(f" - {n}")

if __name__ == '__main__':
    main()
