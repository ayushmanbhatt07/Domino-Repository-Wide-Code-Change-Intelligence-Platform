from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ingestion import RepositoryIngestionService
from analysis import RepositoryAnalyzer


app = FastAPI(
    title="Domino",
    version="0.1",
    description="Repository-Wide Code Change Intelligence Platform"
)


service = RepositoryIngestionService()
analyzer = RepositoryAnalyzer()


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

        result = analyzer.analyze(request.path)

        return {
            "status": "success",
            **result
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Analysis failed."
        )