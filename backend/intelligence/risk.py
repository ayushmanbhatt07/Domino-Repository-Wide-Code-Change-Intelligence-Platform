from impact_analysis.models import ImpactAnalysisResponse

class RiskScorer:
    def __init__(self, hotspot_id_fn):
        self.get_hotspots = hotspot_id_fn # function(repo) -> set of hotspot ids

    def calculate_risk(self, repo: str, impact: ImpactAnalysisResponse) -> dict:
        score = 0
        reasons = []
        
        try:
            hotspots = self.get_hotspots(repo)
        except Exception:
            hotspots = set()
            
        all_impacted = []
        if impact.impacted:
            all_impacted.extend(impact.impacted.files)
            all_impacted.extend(impact.impacted.functions)
            all_impacted.extend(impact.impacted.classes)
            all_impacted.extend(impact.impacted.routes)
            
        # High depth
        max_depth = max([e.depth for e in all_impacted] + [0])
        if max_depth >= 3:
            score += 20
            reasons.append(f"High traversal depth ({max_depth})")
            
        # Exposes Route
        if impact.impacted.routes:
            score += 30
            reasons.append(f"Exposes {len(impact.impacted.routes)} API Routes")
            
        # Hits hotspot
        hit_hotspots = [e.id for e in all_impacted if e.id in hotspots]
        if hit_hotspots:
            score += 25
            reasons.append(f"Affects {len(hit_hotspots)} hotspot(s)")
            
        # Uncertainty
        ambig = [e for e in all_impacted if getattr(e, 'via_ambiguous', False)]
        if ambig:
            score += 10
            reasons.append(f"Path contains ambiguous resolutions ({len(ambig)} nodes)")
            
        # The Test Gap score (+15) will be added by test_recommender logic, 
        # but we can do a preliminary check here if we know tests
        # or we just return this and let test recommender add to it.
        # Let's encapsulate here: if test recommender is run, it can modify.
        
        return {
            "score": min(score, 100),
            "reasons": reasons
        }
