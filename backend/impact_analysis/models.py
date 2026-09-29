from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator

class EntitySelector(BaseModel):
    file_name: Optional[str] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    route: Optional[str] = None
    method: Optional[str] = None
    entity_id: Optional[str] = None
    qualified_name: Optional[str] = None

    @model_validator(mode='after')
    def check_one_selector(self):
        fields = ["file_name", "function_name", "class_name", "route", "entity_id", "qualified_name"]
        provided = [f for f in fields if getattr(self, f) is not None]
        # Allow file_name as a disambiguator for function_name or class_name
        if len(provided) > 1:
            if "file_name" in provided and len(provided) == 2 and ("function_name" in provided or "class_name" in provided):
                pass
            else:
                raise ValueError("Must provide exactly one primary selector (file_name, function_name, class_name, route, entity_id, or qualified_name). file_name can be combined with function_name/class_name.")
        elif len(provided) == 0:
            raise ValueError("Must provide at least one selector.")
            
        for p in provided:
            if getattr(self, p) == "":
                raise ValueError(f"{p} cannot be empty.")
        return self

class ImpactAnalysisRequest(EntitySelector):
    repo: str
    changes: Optional[List[EntitySelector]] = None
    depth: int = Field(default=3, ge=1, le=10)
    import_depth: int = Field(default=1, ge=0, le=3)
    include_dependencies: bool = False
    include_tests: bool = True
    min_confidence: float = 0.0
    max_nodes: int = 500

class PathEdge(BaseModel):
    node: str
    edge_type: str
    resolution: str

class ImpactedEntity(BaseModel):
    id: str
    name: Optional[str] = None
    qualified_name: Optional[str] = None
    type: str
    file: Optional[str] = None
    depth: int
    min_confidence: float
    via_ambiguous: bool
    paths: List[List[PathEdge]] = []

class GroupedEntities(BaseModel):
    files: List[ImpactedEntity] = []
    functions: List[ImpactedEntity] = []
    classes: List[ImpactedEntity] = []
    routes: List[ImpactedEntity] = []
    tests: List[ImpactedEntity] = []
    
class ImpactAnalysisResponse(BaseModel):
    changed_entities: List[Dict[str, Any]]
    impacted: GroupedEntities
    dependencies: Optional[GroupedEntities] = None
    summary: Dict[str, int]
    truncated: bool
    warnings: List[str] = []