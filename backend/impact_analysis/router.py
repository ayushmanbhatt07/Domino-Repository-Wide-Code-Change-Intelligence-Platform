from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from .models import ImpactAnalysisRequest, ImpactAnalysisResponse
from .service import ImpactAnalysisService
from graph_store import Neo4jGraphStore

router = APIRouter()
store = Neo4jGraphStore()
impact_service = ImpactAnalysisService(store)

@router.post("/impact-analysis", response_model=ImpactAnalysisResponse)
def impact_analysis(request: ImpactAnalysisRequest):
    try:
        res = impact_service.analyze(request)
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

@router.get("/repos")
def list_repos():
    try:
        return {"repos": store.list_repos()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repos/{repo}/summary")
def repo_summary(repo: str):
    try:
        res = store.repo_summary(repo)
        if not res:
            raise HTTPException(status_code=404, detail="Repository not found")
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repos/{repo}/entities")
def search_entities(repo: str, type: Optional[str] = None, q: Optional[str] = None):
    try:
        # q is used for name matching
        res = store.find_entities(repo, type=type, name=q, limit=50)
        return {"entities": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
