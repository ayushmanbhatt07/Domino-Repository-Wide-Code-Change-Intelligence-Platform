from typing import Optional

from pydantic import BaseModel, Field


class ImpactAnalysisRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier stored in Neo4j")

    file_name: Optional[str] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    route: Optional[str] = None

    depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum graph traversal depth"
    )

class ImpactedNode(BaseModel):
    id: str
    type: str
    name: Optional[str] = None


class ImpactAnalysisResponse(BaseModel):
    status: str
    changed_entity: ImpactedNode
    impacted_nodes: list[ImpactedNode]