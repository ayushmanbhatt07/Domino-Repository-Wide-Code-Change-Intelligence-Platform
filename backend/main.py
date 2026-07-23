from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ingestion import RepositoryIngestionService
from analysis import RepositoryAnalyzer
from dependency_graph import DependencyGraphBuilder

app = FastAPI(
    title="Domino",
    version="0.1",
    description="Repository-Wide Code Change Intelligence Platform"
)


service = RepositoryIngestionService()
analyzer = RepositoryAnalyzer()
graph_builder = DependencyGraphBuilder()

# -----------------------------
# Request Model
# -----------------------------
class RepositoryRequest(BaseModel):
    repo_url: str


class AnalyzeRequest(BaseModel):
    path: str


# -----------------------------
# Home
# -----------------------------
@app.get("/")
def home():

    return {
        "message": "Domino Backend Running"
    }


# -----------------------------
# Repository Ingestion
# -----------------------------
@app.post("/ingest")
def ingest_repository(request: RepositoryRequest):

    try:

        result = service.ingest(request.repo_url)

        return {
            "status": "success",
            "repository": result["repository"],
            "local_path": result["path"],
            "message": "Repository cloned successfully."
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except RuntimeError as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -----------------------------
# Repository Analysis
# -----------------------------
@app.post("/analyze")
def analyze_repository(request: AnalyzeRequest):

    try:

        # -----------------------------
        # Stage 2 - Repository Analysis
        # -----------------------------
        result = analyzer.analyze(request.path)

        # -----------------------------
        # Stage 3 - Dependency Graph
        # Create a fresh graph builder for every request
        # -----------------------------
        graph_builder = DependencyGraphBuilder()

        graph = graph_builder.build(result)

        # -----------------------------
        # Print Graph Summary
        # -----------------------------
        print("\n========== GRAPH SUMMARY ==========")
        print(graph_builder.summary())

        # -----------------------------
        # Print All Nodes
        # -----------------------------
        print("\n========== NODES ==========")

        for node, data in graph.nodes(data=True):
            print(node, data)

        # -----------------------------
        # Print All Edges
        # -----------------------------
        print("\n========== EDGES ==========")

        for source, target, data in graph.edges(data=True):
            print(f"{source} --{data['relation']}--> {target}")

        # -----------------------------
        # Export Graph
        # -----------------------------
        graph_builder.export_graphml("repository.graphml")

        # -----------------------------
        # API Response
        # -----------------------------
        return {
            "status": "success",
            "graph_summary": graph_builder.summary(),
            **result
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )