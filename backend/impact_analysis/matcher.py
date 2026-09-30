import difflib
from .models import EntitySelector

class ImpactMatcher:
    def __init__(self, graph_store):
        self.graph_store = graph_store

    def match(self, repo: str, selector: EntitySelector):
        candidates = []
        
        if selector.entity_id:
            cands = self.graph_store.get_nodes(repo, [selector.entity_id])
            if cands: return {"status": "FOUND", "nodes": cands}
            
        if selector.qualified_name:
            cands = self.graph_store.find_entities(repo, qualified_name=selector.qualified_name)
            if cands:
                return self._handle_candidates(cands, selector.file_name)
                
        if selector.function_name:
            cands = self.graph_store.find_entities(repo, type="Function", name=selector.function_name)
            if cands:
                return self._handle_candidates(cands, selector.file_name)
                
        if selector.class_name:
            cands = self.graph_store.find_entities(repo, type="Class", name=selector.class_name)
            if cands:
                return self._handle_candidates(cands, selector.file_name)
                
        if selector.file_name:
            # Suffix match
            # Get all files and filter locally to avoid complex Neo4j query
            files = self.graph_store.find_entities(repo, type="File", limit=10000)
            norm = selector.file_name.replace("\\", "/")
            cands = [f for f in files if f["path"].endswith(norm)]
            if cands:
                return self._handle_candidates(cands, None)
                
        if selector.route:
            cands = self.graph_store.find_entities(repo, type="Route")
            # match template
            import re
            matched = []
            for c in cands:
                if selector.method and c.get("method", "").lower() != selector.method.lower():
                    continue
                # Exact or regex match
                if c["path"] == selector.route:
                    matched.append(c)
                else:
                    pattern = re.sub(r'\{[^}]+\}', '[^/]+', c["path"])
                    if re.match(f"^{pattern}$", selector.route):
                        matched.append(c)
            if matched:
                return self._handle_candidates(matched, None)
                
        # NOT_FOUND - gather suggestions
        all_names = []
        # we can just fetch all names from Neo4j (limit to avoid OOM)
        # for fuzzy matching we might just match against a small subset
        nodes = self.graph_store.find_entities(repo, limit=2000)
        target = selector.function_name or selector.class_name or selector.file_name or selector.route or selector.qualified_name
        if target and nodes:
            names = [n.get("name") or n.get("path") or "" for n in nodes]
            suggestions = difflib.get_close_matches(target, names, n=5, cutoff=0.3)
            return {"status": "NOT_FOUND", "suggestions": suggestions}
            
        return {"status": "NOT_FOUND", "suggestions": []}
        
    def _handle_candidates(self, cands, file_name):
        if file_name:
            norm = file_name.replace("\\", "/")
            cands = [c for c in cands if norm in c.get("path", "")]
            
        if len(cands) == 1:
            return {"status": "FOUND", "nodes": cands}
        elif len(cands) > 1:
            return {"status": "AMBIGUOUS", "nodes": cands}
        else:
            return {"status": "NOT_FOUND", "suggestions": []}