from fastapi import APIRouter, HTTPException
from .models import ReasonRequest, ReasonResponse
from .reasoning_service import ReasoningService
from impact_analysis.service import ImpactAnalysisService
from graph_store import Neo4jGraphStore

router = APIRouter()

store = Neo4jGraphStore()
impact_service = ImpactAnalysisService(store)
reasoning_service = ReasoningService(impact_service, store)

@router.post("/reason", response_model=ReasonResponse)
def get_ai_reasoning(request: ReasonRequest):
    try:
        res = reasoning_service.reason(request)
        return res
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
