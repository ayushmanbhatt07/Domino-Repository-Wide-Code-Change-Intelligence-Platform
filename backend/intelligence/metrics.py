import networkx as nx

class GraphMetricsCache:
    def __init__(self, store):
        self.store = store
        self.graphs = {}
        
    def get_graph(self, repo: str) -> nx.DiGraph:
        if repo not in self.graphs:
            self.graphs[repo] = self.store.load_repo_graph(repo)
        return self.graphs[repo]
        
    def invalidate(self, repo: str):
        if repo in self.graphs:
            del self.graphs[repo]

class MetricsCalculator:
    def __init__(self, cache: GraphMetricsCache):
        self.cache = cache
        
    def calculate_fan_in(self, repo: str) -> dict:
        # Number of incoming edges
        g = self.cache.get_graph(repo)
        return {n: g.in_degree(n) for n in g.nodes()}
        
    def calculate_reverse_reach(self, repo: str) -> dict:
        # How many nodes depend on this node (upstream BFS)
        g = self.cache.get_graph(repo)
        reach = {}
        # Simple approximation or exact
        for n in g.nodes():
            # count ancestors
            ancestors = nx.ancestors(g, n)
            reach[n] = len(ancestors)
        return reach
