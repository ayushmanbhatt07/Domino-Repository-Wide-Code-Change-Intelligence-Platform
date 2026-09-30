from impact_analysis.models import ImpactAnalysisRequest
from intelligence.hotspots import HotspotIdentifier
from intelligence.risk import RiskScorer
from intelligence.test_recommender import TestRecommender
from intelligence.metrics import GraphMetricsCache, MetricsCalculator
from ai_reasoning.context_builder import ContextBuilder

from .models import ChangeRequest, ChangePlanResponse, PatchRequest, PatchResponse
from .planner import ChangePlannerLLMService
from .patch_validator import PatchValidator

class ChangePlanningService:
    def __init__(self, impact_service, store):
        self.impact_service = impact_service
        self.metrics_cache = GraphMetricsCache(store)
        self.metrics_calc = MetricsCalculator(self.metrics_cache)
        self.hotspot_id = HotspotIdentifier(self.metrics_calc)
        self.risk_scorer = RiskScorer(self.hotspot_id.get_hotspot_set)
        self.test_rec = TestRecommender(self.metrics_cache)
        
        self.context_builder = ContextBuilder()
        self.llm_service = ChangePlannerLLMService()
        self.patch_validator = PatchValidator()

    def plan_change(self, request: ChangeRequest) -> ChangePlanResponse:
        repo = request.repo
        
        # 1. Run Impact Analysis (Stage 5)
        impact_req = ImpactAnalysisRequest(
            repo=repo,
            file_name=request.target_entity.file_name if request.target_entity else None,
            function_name=request.target_entity.function_name if request.target_entity else None,
            class_name=request.target_entity.class_name if request.target_entity else None,
            route=request.target_entity.route if request.target_entity else None,
            method=request.target_entity.method if request.target_entity else None,
            entity_id=request.target_entity.entity_id if request.target_entity else None,
            qualified_name=request.target_entity.qualified_name if request.target_entity else None,
            depth=4
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
            
        # 3. Build Context (Reusing Stage 7 logic)
        context = self.context_builder.build_context(
            repo_id=repo,
            target=target,
            impact_res=impact,
            risk_res=risk,
            tests_res=tests,
            hotspots_res=hotspots_list,
            question=request.request
        )
        
        # 4. Invoke Planner (Stage 8)
        change_plan = self.llm_service.generate_plan(request.request, context)
        error = None
        if not change_plan:
            error = "AI Provider unavailable or returned invalid output."
            
        return ChangePlanResponse(
            change_plan=change_plan,
            impact=impact.summary,
            risk={"score": risk["score"], "reasons": risk["reasons"]},
            evidence=[e.get("id") for e in impact.changed_entities] + all_impacted_ids,
            error=error
        )

    def generate_patch(self, request: PatchRequest, context_override: str = "") -> PatchResponse:
        # Generate the unified diff patch based on the plan
        plan_json = request.plan.model_dump_json()
        
        patch_text = self.llm_service.generate_patch(request.change_request, plan_json, context_override)
        if not patch_text:
            patch_text = ""
            
        if "```diff" in patch_text:
            patch_text = patch_text.split("```diff")[1].split("```")[0].strip()
        elif "```" in patch_text:
            patch_text = patch_text.split("```")[1].split("```")[0].strip()
            
        val_res = self.patch_validator.validate(patch_text, request.plan)
        
        return PatchResponse(
            patch=patch_text,
            files_changed=val_res["files_changed"],
            validation=val_res,
            warnings=val_res["warnings"]
        )
