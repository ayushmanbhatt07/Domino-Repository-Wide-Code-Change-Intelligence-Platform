from pathlib import Path
from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from ingestion import RepositoryIngestionService
from analysis import RepositoryAnalyzer
from dependency_graph import DependencyGraphBuilder
from graph_store import Neo4jGraphStore

from impact_analysis.router import router as impact_router

store = Neo4jGraphStore()
service = RepositoryIngestionService()
analyzer = RepositoryAnalyzer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        store.ensure_schema()
    except Exception as e:
        print("Schema setup failed:", e)
    yield
    # Shutdown
    store.close()

app = FastAPI(
    title="Domino",
    version="0.2",
    description="Repository-Wide Code Change Intelligence Platform",
    lifespan=lifespan
)

app.include_router(impact_router)

class RepositoryRequest(BaseModel):
    repo_url: str
    repo_name: Optional[str] = None

class AnalyzeRequest(BaseModel):
    path: str
    repo_name: str
    commit_sha: str = "unknown"
    keep_clone: bool = False
    export_graphml: bool = False

@app.get("/")
def home():
    return {"message": "Domino Backend Running"}

@app.post("/ingest")
def ingest_repository(request: RepositoryRequest):
    try:
        result = service.ingest(request.repo_url, request.repo_name)
        return {
            "status": "success",
            "repository": result["repository"],
            "local_path": result["path"],
            "commit_sha": result["commit_sha"],
            "message": "Repository cloned successfully."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
def analyze_repository(request: AnalyzeRequest):
    try:
        result = analyzer.analyze(request.path)
        result["summary"]["repository"] = request.repo_name
        result["commit_sha"] = request.commit_sha
        
        graph_builder = DependencyGraphBuilder()
        graph = graph_builder.build(result)
        
        graph_file = None
        if request.export_graphml:
            repo_name = request.repo_name
            graph_file = f"graphs/{repo_name}_{uuid.uuid4().hex[:8]}.graphml"
            graph_builder.export_graphml(graph_file)
            
        try:
            store.save(request.repo_name, graph)
            stored_in_neo4j = True
        except Exception as e:
            print("Neo4j store failed:", e)
            stored_in_neo4j = False
            
        return {
            "status": "success",
            "graph_summary": graph_builder.summary(),
            "graph_file": graph_file,
            "stored_in_neo4j": stored_in_neo4j
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if not request.keep_clone:
            service.cleanup(request.path)