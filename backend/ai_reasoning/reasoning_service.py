from impact_analysis.models import ImpactAnalysisRequest
from intelligence.hotspots import HotspotIdentifier
from intelligence.risk import RiskScorer
from intelligence.test_recommender import TestRecommender
from intelligence.metrics import GraphMetricsCache, MetricsCalculator
from .models import ReasonRequest, ReasonResponse
from .context_builder import ContextBuilder
from .llm_service import LLMService

class ReasoningService:
    def __init__(self, impact_service, store):
        self.impact_service = impact_service
        self.metrics_cache = GraphMetricsCache(store)
        self.metrics_calc = MetricsCalculator(self.metrics_cache)
        self.hotspot_id = HotspotIdentifier(self.metrics_calc)
        self.risk_scorer = RiskScorer(self.hotspot_id.get_hotspot_set)
        self.test_rec = TestRecommender(self.metrics_cache)
        
        self.context_builder = ContextBuilder()
        self.llm_service = LLMService()

    def reason(self, request: ReasonRequest) -> ReasonResponse:
        repo = request.repo
        
        # 1. Run Impact Analysis (Stage 5)
        # We reuse the ImpactAnalysisRequest schema
        impact_req = ImpactAnalysisRequest(
            repo=repo,
            file_name=request.target.file_name,
            function_name=request.target.function_name,
            class_name=request.target.class_name,
            route=request.target.route,
            method=request.target.method,
            entity_id=request.target.entity_id,
            qualified_name=request.target.qualified_name,
            depth=3 # default depth for reasoning
        )
        
        impact = self.impact_service.analyze(impact_req)
        target = impact.changed_entities[0] if impact.changed_entities else {}
        
        # 2. Run Intelligence (Stage 6)
        hotspots_list = self.hotspot_id.identify_hotspots(repo, top_n=10)
        risk = self.risk_scorer.calculate_risk(repo, impact)
        
        all_impacted_ids = []
        if impact.impacted:
            for g in (impact.impacted.files, impact.impacted.functions, impact.impacted.classes, impact.impacted.routes):
                all_impacted_ids.extend([e.id for e in g])
                
        tests = self.test_rec.recommend(repo, all_impacted_ids)
        if tests["untested_impacted"]:
            risk["score"] = min(100, risk["score"] + 15)
            risk["reasons"].append(f"Test gap: {len(tests['untested_impacted'])} impacted nodes have NO test coverage")
            
        # 3. Build Context
        context = self.context_builder.build_context(
            repo_id=repo,
            target=target,
            impact_res=impact,
            risk_res=risk,
            tests_res=tests,
            hotspots_res=hotspots_list,
            question=request.question,
            limit=request.context_size_limit
        )
        
        # 4. Invoke LLM (Stage 7)
        ai_reasoning = self.llm_service.generate_reasoning(context)
        error = None
        if not ai_reasoning:
            error = "AI Provider unavailable or returned invalid output."
            
        return ReasonResponse(
            target=target,
            impact_summary=impact.summary,
            risk_summary={"score": risk["score"], "reasons": risk["reasons"]},
            ai_reasoning=ai_reasoning,
            error=error
        )
