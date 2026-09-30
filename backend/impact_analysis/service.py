from .models import ImpactAnalysisRequest, ImpactAnalysisResponse, GroupedEntities, ImpactedEntity
from .matcher import ImpactMatcher
from .traversal import ImpactTraversal

class ImpactAnalysisService:
    def __init__(self, graph_store):
        self.graph_store = graph_store
        self.matcher = ImpactMatcher(graph_store)
        self.traversal = ImpactTraversal(graph_store)
        
    def analyze(self, request: ImpactAnalysisRequest) -> ImpactAnalysisResponse:
        repo = request.repo
        
        # Match
        match_res = self.matcher.match(repo, request)
        if match_res["status"] != "FOUND":
            # If not found or ambiguous, we could raise an error or return a specific response
            raise ValueError(f"Match status: {match_res['status']}. Candidates/Suggestions: {match_res.get('nodes') or match_res.get('suggestions')}")
            
        changed_entities = match_res["nodes"]
        
        # Seed Expansion
        seeds = set()
        for e in changed_entities:
            seeds.add(e["id"])
            if e["type"].lower() == "file":
                # file contains -> class | function
                contained = self.graph_store.neighbors(repo, [e["id"]], "out", ["CONTAINS"])
                for c in contained: seeds.add(c["dst"])
            elif e["type"].lower() == "class":
                # class contains -> method
                contained = self.graph_store.neighbors(repo, [e["id"]], "out", ["CONTAINS"])
                for c in contained: seeds.add(c["dst"])
            elif e["type"].lower() == "route":
                # route handled_by -> function
                handled = self.graph_store.neighbors(repo, [e["id"]], "out", ["HANDLED_BY"])
                for h in handled: seeds.add(h["dst"])
                
        seeds_list = list(seeds)
        
        # Traversal Upstream (Impact)
        impacted_data, imp_trunc = self.traversal.upstream_impact(
            repo, seeds_list, depth=request.depth, import_depth=request.import_depth, 
            min_confidence=request.min_confidence, max_nodes=request.max_nodes
        )
        
        # Traversal Downstream (Dependencies)
        deps_data = []
        dep_trunc = False
        if request.include_dependencies:
            deps_data, dep_trunc = self.traversal.downstream_dependencies(
                repo, seeds_list, depth=request.depth, import_depth=request.import_depth, 
                min_confidence=request.min_confidence, max_nodes=request.max_nodes
            )
            
        # Group
        def group_entities(data_list):
            res = GroupedEntities()
            for d in data_list:
                t = d.get("type", "").lower()
                is_test = d.get("is_test", False)
                
                ent = ImpactedEntity(**d)
                
                if is_test and request.include_tests:
                    res.tests.append(ent)
                elif t == "file":
                    res.files.append(ent)
                elif t == "class":
                    res.classes.append(ent)
                elif t == "function":
                    res.functions.append(ent)
                elif t == "route":
                    res.routes.append(ent)
            return res
            
        impacted = group_entities(impacted_data)
        deps = group_entities(deps_data) if request.include_dependencies else None
        
        # Summary
        summary = {
            "impacted_files": len(impacted.files),
            "impacted_functions": len(impacted.functions),
            "impacted_classes": len(impacted.classes),
            "impacted_routes": len(impacted.routes),
            "impacted_tests": len(impacted.tests)
        }
        
        return ImpactAnalysisResponse(
            changed_entities=changed_entities,
            impacted=impacted,
            dependencies=deps,
            summary=summary,
            truncated=imp_trunc or dep_trunc,
            warnings=[]
        )
