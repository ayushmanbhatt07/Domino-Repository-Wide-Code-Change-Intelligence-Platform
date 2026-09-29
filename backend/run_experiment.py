import sys
from pathlib import Path
from analysis import RepositoryAnalyzer
from dependency_graph import DependencyGraphBuilder
import json

def run():
    analyzer = RepositoryAnalyzer()
    analysis = analyzer.analyze("d:/Domino-Repository-Wide-Code-Change-Intelligence-Platform/backend")
    
    # Save a sample analyzer output JSON
    with open("analyzer_output.json", "w") as f:
        json.dump(analysis, f, indent=2)
        
    builder = DependencyGraphBuilder()
    graph = builder.build(analysis)
    
    # node and edge counts by type
    node_types = {}
    for _, data in graph.nodes(data=True):
        ntype = data.get("type", "unknown")
        node_types[ntype] = node_types.get(ntype, 0) + 1
        
    edge_types = {}
    for _, _, data in graph.edges(data=True):
        etype = data.get("relation", "unknown")
        edge_types[etype] = edge_types.get(etype, 0) + 1
        
    print("NODE TYPES:", json.dumps(node_types))
    print("EDGE TYPES:", json.dumps(edge_types))
    
    summary = builder.summary()
    print("SUMMARY:", json.dumps(summary))
    
    # external nodes
    external_calls = [n for n, data in graph.nodes(data=True) if data.get("type") == "external"]
    print("EXTERNAL CALLS:", json.dumps(external_calls[:10]))
    
    with open("graph_nodes.json", "w") as f:
        nodes = [{"id": n, **data} for n, data in graph.nodes(data=True)]
        json.dump(nodes, f, indent=2)

    with open("graph_edges.json", "w") as f:
        edges = [{"source": u, "target": v, **data} for u, v, data in graph.edges(data=True)]
        json.dump(edges, f, indent=2)
        
if __name__ == "__main__":
    run()
