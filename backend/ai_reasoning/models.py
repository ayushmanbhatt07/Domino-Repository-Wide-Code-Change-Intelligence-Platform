from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from impact_analysis.models import EntitySelector

class ReasonRequest(BaseModel):
    repo: str
    target: EntitySelector
    question: Optional[str] = None
    context_size_limit: int = Field(default=20000, description="Max character limit for source code context")

class EvidenceItem(BaseModel):
    entity_id: Optional[str] = None
    qualified_name: Optional[str] = None
    file_path: Optional[str] = None
    source_line_range: Optional[str] = None
    relationship_type: Optional[str] = None
    dependency_path: Optional[str] = None

class AIExplanation(BaseModel):
    summary: str = Field(description="A concise summary of the change and its implications")
    impact_explanation: str = Field(description="Explanation of what depends on this entity and how impact propagates")
    risk_explanation: str = Field(description="Breakdown of the calculated risk components and why they matter")
    affected_components: List[str] = Field(description="List of significant components, files, or routes affected")
    testing_guidance: str = Field(description="Guidance on what to test based on coverage gaps and recommendations")
    change_considerations: str = Field(description="Engineering suggestions and potential side effects to watch out for")
    evidence: List[EvidenceItem] = Field(description="Specific graph or source evidence supporting the explanation")
    limitations: List[str] = Field(description="Any limitations, uncertainties, or lack of evidence in the reasoning")

class ReasonResponse(BaseModel):
    target: Dict[str, Any]
    impact_summary: Dict[str, Any]
    risk_summary: Dict[str, Any]
    ai_reasoning: Optional[AIExplanation] = None
    error: Optional[str] = None
