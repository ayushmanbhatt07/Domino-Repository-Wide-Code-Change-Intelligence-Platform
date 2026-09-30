from fastapi import APIRouter, HTTPException
from .models import ChangeRequest, ChangePlanResponse, PatchRequest, PatchResponse, ValidationRequest, ValidationResponse
from .service import ChangePlanningService
from impact_analysis.service import ImpactAnalysisService
from graph_store import Neo4jGraphStore
from .patch_validator import PatchValidator

router = APIRouter()

store = Neo4jGraphStore()
impact_service = ImpactAnalysisService(store)
planning_service = ChangePlanningService(impact_service, store)
validator = PatchValidator()

@router.post("/change/plan", response_model=ChangePlanResponse)
def plan_change(request: ChangeRequest):
    try:
        return planning_service.plan_change(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change/patch", response_model=PatchResponse)
def generate_patch(request: PatchRequest):
    try:
        return planning_service.generate_patch(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change/validate", response_model=ValidationResponse)
def validate_patch(request: ValidationRequest):
    try:
        val_res = validator.validate(request.patch, request.plan)
        return ValidationResponse(**val_res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
