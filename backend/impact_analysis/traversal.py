class ImpactTraversal:

    def __init__(self, graph_store):
        self.graph_store = graph_store

    def downstream(
        self,
        repo: str,
        node_id: str,
        depth: int = 3,
    ):
        return self.graph_store.find_downstream(
            repo=repo,
            node_id=node_id,
            depth=depth
        )