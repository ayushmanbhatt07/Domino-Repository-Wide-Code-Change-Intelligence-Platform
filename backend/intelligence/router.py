from fastapi import APIRouter, HTTPException
from impact_analysis.models import ImpactAnalysisRequest
from impact_analysis.service import ImpactAnalysisService
from graph_store import Neo4jGraphStore
from .metrics import GraphMetricsCache, MetricsCalculator
from .hotspots import HotspotIdentifier
from .risk import RiskScorer
from .test_recommender import TestRecommender
from .report import IntelligenceReportGenerator

router = APIRouter()

store = Neo4jGraphStore()
impact_service = ImpactAnalysisService(store)
metrics_cache = GraphMetricsCache(store)
metrics_calc = MetricsCalculator(metrics_cache)
hotspot_id = HotspotIdentifier(metrics_calc)
risk_scorer = RiskScorer(hotspot_id.get_hotspot_set)
test_rec = TestRecommender(metrics_cache)
report_gen = IntelligenceReportGenerator()

@router.post("/intelligence")
def get_intelligence(request: ImpactAnalysisRequest):
    try:
        # Run Stage 5 Impact Analysis
        impact = impact_service.analyze(request)
        
        repo = request.repo
        
        # Calculate Intelligence components
        hotspots_list = hotspot_id.identify_hotspots(repo, top_n=10)
        risk = risk_scorer.calculate_risk(repo, impact)
        
        all_impacted_ids = []
        if impact.impacted:
            for g in (impact.impacted.files, impact.impacted.functions, impact.impacted.classes, impact.impacted.routes):
                all_impacted_ids.extend([e.id for e in g])
                
        tests = test_rec.recommend(repo, all_impacted_ids)
        
        # Add test gap risk if there are untested nodes
        if tests["untested_impacted"]:
            risk["score"] = min(100, risk["score"] + 15)
            risk["reasons"].append(f"Test gap: {len(tests['untested_impacted'])} impacted nodes have NO test coverage")
            
        # Return combined JSON format (which generator handles)
        res_json = report_gen.generate_json(impact, risk, tests, hotspots_list)
        res_md = report_gen.generate_markdown(impact, risk, tests, hotspots_list)
        
        return {
            "status": "success",
            "report": res_json,
            "markdown": res_md
        }
    except ValueError as e:
        msg = str(e)
        if "AMBIGUOUS" in msg:
            raise HTTPException(status_code=409, detail=msg)
        elif "NOT_FOUND" in msg or "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        else:
            raise HTTPException(status_code=422, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
