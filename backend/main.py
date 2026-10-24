from pathlib import Path
from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from ingestion import RepositoryIngestionService
from analysis import RepositoryAnalyzer
from dependency_graph import DependencyGraphBuilder
from graph_store import Neo4jGraphStore

from impact_analysis.router import router as impact_router
from intelligence.router import router as intelligence_router
from ai_reasoning.router import router as ai_reasoning_router
from self_rag.router import router as self_rag_router, indexer as code_indexer

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
    version="0.3",
    description="Repository-Wide Code Change Intelligence & Self-RAG Assistant",
    lifespan=lifespan
)

app.include_router(impact_router)
app.include_router(intelligence_router)
app.include_router(ai_reasoning_router)
app.include_router(self_rag_router)

class RepositoryRequest(BaseModel):
    repo_url: str
    repo_name: Optional[str] = None

class AnalyzeRequest(BaseModel):
    path: str
    repo_name: str
    commit_sha: str = "unknown"
    keep_clone: bool = False
    export_graphml: bool = False

@app.get("/api/health")
def health():
    return {"message": "Domino Backend Running", "status": "healthy"}

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
    target_path = request.path
    commit_sha = request.commit_sha
    is_remote_url = request.path.startswith("http://") or request.path.startswith("https://") or request.path.endswith(".git")
    
    try:
        # If user passed a GitHub URL into /analyze directly, auto-clone it
        if is_remote_url:
            repo_name_val = request.repo_name if request.repo_name != "string" else None
            ingest_res = service.ingest(request.path, repo_name_val)
            target_path = ingest_res["path"]
            commit_sha = ingest_res["commit_sha"]
            if request.repo_name == "string":
                request.repo_name = ingest_res["repository"]

        result = analyzer.analyze(target_path)
        result["summary"]["repository"] = request.repo_name
        result["commit_sha"] = commit_sha
        
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
            
        # Index in ChromaDB & BM25 for Self-RAG
        try:
            indexed_count = code_indexer.index_repository(request.repo_name, result)
        except Exception as e:
            print("Self-RAG indexing failed:", e)
            indexed_count = 0
            
        return {
            "status": "success",
            "graph_summary": graph_builder.summary(),
            "graph_file": graph_file,
            "stored_in_neo4j": stored_in_neo4j,
            "indexed_code_chunks": indexed_count
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if not request.keep_clone and is_remote_url:
            service.cleanup(target_path)

# Serve Modern Dashboard Frontend
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")