from typing import List, Dict, Any, Optional
from .code_indexer import CodeIndexer

class HybridRetriever:
    """
    Hybrid Retriever that fuses:
    1. Lexical Search (BM25)
    2. Dense Vector Search (ChromaDB)
    3. Graph Structural Expansion (Domino NetworkX / Neo4j Graph)
    via Reciprocal Rank Fusion (RRF).
    """
    def __init__(self, indexer: CodeIndexer, graph_store=None):
        self.indexer = indexer
        self.graph_store = graph_store

    def retrieve(self, repo_id: str, query: str, top_k: int = 5, expand_graph: bool = True) -> List[Dict[str, Any]]:
        collection_name = f"repo_{repo_id.replace('-', '_').replace('/', '_')}"
        
        # 1. BM25 Search
        bm25_results = []
        if repo_id in self.indexer.bm25_indices:
            bm25_results = self.indexer.bm25_indices[repo_id].search(query, top_k=top_k * 2)

        # 2. Dense Vector Search (ChromaDB)
        chroma_results = []
        try:
            collection = self.indexer.chroma_client.get_collection(
                name=collection_name,
                embedding_function=self.indexer.embedding_fn
            )
            res = collection.query(query_texts=[query], n_results=min(top_k * 2, collection.count() or 1))
            if res and res.get("ids") and res["ids"][0]:
                for idx, cid in enumerate(res["ids"][0]):
                    dist = res["distances"][0][idx] if "distances" in res and res["distances"] else 0.0
                    meta = res["metadatas"][0][idx] if "metadatas" in res and res["metadatas"] else {}
                    chroma_results.append({
                        "id": cid,
                        "distance": dist,
                        "metadata": meta
                    })
        except Exception as e:
            # Fallback if collection not ready or empty
            pass

        # 3. Reciprocal Rank Fusion (RRF)
        # score(d) = sum(1 / (k + rank))
        rrf_k = 60.0
        fused_scores: Dict[str, float] = {}

        for rank, item in enumerate(bm25_results):
            cid = item["id"]
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank + 1))

        for rank, item in enumerate(chroma_results):
            cid = item["id"]
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank + 1))

        # Sort by fused score
        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)[:top_k]

        final_candidates = []
        for cid in sorted_ids:
            chunk = self.indexer.get_chunk(cid)
            if not chunk:
                continue
            
            cand = {
                "id": cid,
                "score": fused_scores[cid],
                "code": chunk.get("code", ""),
                "metadata": chunk.get("metadata", {}),
                "graph_context": {}
            }

            # 4. Graph Structural Expansion (Enrich with Callers & Callees from Domino Graph)
            if expand_graph and self.graph_store:
                cand["graph_context"] = self._fetch_graph_context(repo_id, chunk["metadata"])

            final_candidates.append(cand)

        return final_candidates

    def _fetch_graph_context(self, repo_id: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetches immediate callers and callees for the candidate from the Domino dependency graph.
        """
        context = {"callers": [], "callees": [], "routes": []}
        qual_name = meta.get("qualified_name") or meta.get("name")
        if not qual_name or not self.graph_store:
            return context

        try:
            # Query Neo4j / NetworkX graph store for CALLS relationships
            with self.graph_store.driver.session() as session:
                # Callers: (caller)-[:CALLS]->(target)
                q_callers = """
                MATCH (caller)-[:CALLS]->(target {repo: $repo})
                WHERE target.qualified_name = $qname OR target.name = $qname
                RETURN caller.qualified_name AS caller_name, caller.file AS file
                LIMIT 5
                """
                res_callers = session.run(q_callers, repo=repo_id, qname=qual_name)
                context["callers"] = [f"{r['caller_name']} ({r['file']})" for r in res_callers]

                # Callees: (target)-[:CALLS]->(callee)
                q_callees = """
                MATCH (target {repo: $repo})-[:CALLS]->(callee)
                WHERE target.qualified_name = $qname OR target.name = $qname
                RETURN callee.qualified_name AS callee_name, callee.file AS file
                LIMIT 5
                """
                res_callees = session.run(q_callees, repo=repo_id, qname=qual_name)
                context["callees"] = [f"{r['callee_name']} ({r['file']})" for r in res_callees]
        except Exception:
            # Gracefully handle if neo4j is offline
            pass

        return context
