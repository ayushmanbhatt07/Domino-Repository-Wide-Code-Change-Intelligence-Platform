from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from impact_analysis.models import EntitySelector

class ChangeRequest(BaseModel):
    repo: str
    request: str
    target_entity: Optional[EntitySelector] = None
    file_constraint: Optional[str] = None
    change_scope: Optional[str] = None
    generate_patch: bool = False

class AffectedComponent(BaseModel):
    path: Optional[str] = Field(None, description="File path if applicable")
    symbol: Optional[str] = Field(None, description="Function, class, or route name")
    reason: str = Field(description="Why this component is affected")
    source: Literal["graph_verified", "source_verified", "llm_inferred", "llm_proposed"] = Field(
        description="Source of this determination"
    )
    confidence: str = Field(description="High, Medium, or Low")

class ImplementationStep(BaseModel):
    step_number: int
    description: str
    target_file: Optional[str] = None
    target_symbol: Optional[str] = None

class ValidationStep(BaseModel):
    step_number: int
    description: str

class ChangePlan(BaseModel):
    summary: str
    requested_change: str
    affected_files: List[AffectedComponent]
    affected_functions: List[AffectedComponent]
    affected_classes: List[AffectedComponent]
    affected_routes: List[AffectedComponent]
    implementation_steps: List[ImplementationStep]
    dependency_changes: List[str]
    configuration_changes: List[str]
    database_changes: List[str]
    api_changes: List[str]
    test_changes: List[str]
    potential_breaking_changes: List[str]
    risk_considerations: List[str]
    assumptions: List[str]
    evidence: List[str]
    validation_steps: List[ValidationStep]
    confidence: str
    limitations: List[str]

class PatchRequest(BaseModel):
    repo: str
    change_request: str
    target_entity: Optional[EntitySelector] = None
    plan: ChangePlan

class ValidationRequest(BaseModel):
    repo: str
    patch: str
    plan: Optional[ChangePlan] = None

class ValidationResponse(BaseModel):
    valid: bool
    syntax_status: str
    scope_status: str
    security_status: str
    test_status: str
    warnings: List[str]

class ChangePlanResponse(BaseModel):
    change_plan: Optional[ChangePlan] = None
    impact: Dict[str, Any]
    risk: Dict[str, Any]
    evidence: List[str]
    error: Optional[str] = None

class PatchResponse(BaseModel):
    patch: str
    files_changed: List[str]
    validation: ValidationResponse
    warnings: List[str]
