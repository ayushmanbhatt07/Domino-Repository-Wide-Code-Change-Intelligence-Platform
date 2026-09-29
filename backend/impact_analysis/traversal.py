class ImpactTraversal:
    def __init__(self, graph_store):
        self.graph_store = graph_store
        
    def _bfs(self, repo, seeds, direction, depth_limit, min_confidence, max_nodes, import_depth):
        # seeds is a list of node ids
        visited = set(seeds)
        queue = [(s, 0, []) for s in seeds]
        
        impacted = {} # id -> {depth, min_confidence, via_ambiguous, paths}
        truncated = False
        
        while queue:
            # Batch process by current depth to use neighbors() efficiently
            curr_depth = queue[0][1]
            if curr_depth >= depth_limit:
                break
                
            # Collect all nodes at curr_depth
            batch = []
            while queue and queue[0][1] == curr_depth:
                batch.append(queue.pop(0))
                
            if not batch: break
            
            node_ids = [b[0] for b in batch]
            edges = self.graph_store.neighbors(repo, node_ids, direction, min_confidence=min_confidence)
            
            # Map edges by src
            edges_by_src = {}
            for e in edges:
                edges_by_src.setdefault(e["src"], []).append(e)
                
            for curr_id, d, path in batch:
                for e in edges_by_src.get(curr_id, []):
                    dst = e["dst"]
                    rel = e["rel"]
                    props = e["props"]
                    
                    if rel == "IMPORTS" and d >= import_depth:
                        continue
                        
                    edge_conf = props.get("confidence", 1.0)
                    res = props.get("resolution", "")
                    
                    new_path = path + [{"node": curr_id, "edge_type": rel, "resolution": res}]
                    new_min_conf = min(edge_conf, 1.0 if not path else min(p.get("confidence", 1.0) for p in path)) # wait, the path only stores node, edge_type, res. We need to compute path conf correctly.
                    
                    # Compute path conf
                    path_conf = edge_conf
                    via_ambig = (res == "ambiguous")
                    
                    # Fetch previous via_ambig from the item in impacted if we can, but since this is BFS, we can track it per path
                    # Let's attach conf and via_ambig to the queue item
                    
                    if dst not in visited:
                        visited.add(dst)
                        if len(impacted) >= max_nodes:
                            truncated = True
                            # drain queue and exit
                            queue = []
                            break
                            
                        # Store in impacted
                        impacted[dst] = {
                            "id": dst,
                            "depth": d + 1,
                            "min_confidence": min_confidence, # placeholder, updated below
                            "via_ambiguous": via_ambig,
                            "paths": [new_path]
                        }
                        queue.append((dst, d + 1, new_path))
                    else:
                        # Already visited. If same depth, we can add the path
                        if dst in impacted and impacted[dst]["depth"] == d + 1:
                            impacted[dst]["paths"].append(new_path)
                            impacted[dst]["via_ambiguous"] = impacted[dst]["via_ambiguous"] or via_ambig
                            
            if truncated:
                break
                
        # Fill in full node data for impacted
        if impacted:
            nodes_data = self.graph_store.get_nodes(repo, list(impacted.keys()))
            for n in nodes_data:
                nid = n["id"]
                if nid in impacted:
                    impacted[nid].update(n)
                    
        return list(impacted.values()), truncated

    def upstream_impact(self, repo, seeds, depth=3, import_depth=1, min_confidence=0.0, max_nodes=500):
        return self._bfs(repo, seeds, "in", depth, min_confidence, max_nodes, import_depth)
        
    def downstream_dependencies(self, repo, seeds, depth=3, import_depth=1, min_confidence=0.0, max_nodes=500):
        return self._bfs(repo, seeds, "out", depth, min_confidence, max_nodes, import_depth)