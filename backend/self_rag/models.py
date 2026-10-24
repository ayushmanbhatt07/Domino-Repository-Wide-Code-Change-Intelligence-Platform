from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RetrievalDecision(BaseModel):
    needs_retrieval: bool = Field(description="True if codebase retrieval is required, False for general questions")
    decision_token: str = Field(description="[Retrieve] or [NoRetrieve]")
    rationale: str = Field(description="Reasoning behind retrieval decision")

class RelevanceCritique(BaseModel):
    is_relevant: bool = Field(description="Whether the retrieved snippet is relevant to the user query")
    relevance_token: str = Field(description="[IsRel] or [NotRel]")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    rationale: str = Field(description="Critique rationale")

class GroundingCritique(BaseModel):
    is_supported: bool = Field(description="Whether all generated code and explanations are strictly grounded in retrieved context")
    grounding_token: str = Field(description="[IsSup], [PartSup], or [NoSup]")
    hallucinated_symbols: List[str] = Field(default_factory=list, description="Any invented functions, classes, or endpoints")
    rationale: str = Field(description="Evaluation of factual grounding")

class UtilityCritique(BaseModel):
    utility_score: int = Field(ge=1, le=5, description="Utility score from 1 (unhelpful) to 5 (excellent)")
    utility_token: str = Field(description="[IsUse:1] to [IsUse:5]")
    is_acceptable: bool = Field(description="True if score >= 3 and meets developer criteria")
    feedback: str = Field(description="Actionable critique of the output")

class ReflectionTrace(BaseModel):
    retrieval_decision: RetrievalDecision
    relevance_critiques: List[Dict[str, Any]] = Field(default_factory=list)
    grounding_critique: Optional[GroundingCritique] = None
    utility_critique: Optional[UtilityCritique] = None
    retries_count: int = 0

class QARequest(BaseModel):
    repo_id: str
    query: str
    top_k: int = 4
    enable_reflection: bool = True

class QAResponse(BaseModel):
    query: str
    answer: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    reflection_trace: ReflectionTrace
    error: Optional[str] = None

class RefactorRequest(BaseModel):
    repo_id: str
    target_entity: str # e.g. "backend/main.py::get_db"
    instructions: str  # e.g. "Convert to async SQLAlchemy session with connection pooling"
    enable_reflection: bool = True

class RefactorResponse(BaseModel):
    target_entity: str
    proposed_code: str
    diff: str
    syntax_valid: bool
    syntax_error: Optional[str] = None
    impacted_callers_count: int
    impacted_routes: List[str] = Field(default_factory=list)
    recommended_tests: List[str] = Field(default_factory=list)
    caller_diffs: Dict[str, str] = Field(default_factory=list)
    reflection_trace: ReflectionTrace
    error: Optional[str] = None
