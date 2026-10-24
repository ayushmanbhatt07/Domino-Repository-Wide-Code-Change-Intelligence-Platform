from fastapi import APIRouter, HTTPException
from .models import (
    QARequest,
    QAResponse,
    RefactorRequest,
    RefactorResponse
)
from .qa_service import SelfRAGQAService
from .refactor_service import SelfRAGRefactorService
from retrieval.code_indexer import CodeIndexer
from retrieval.hybrid_retriever import HybridRetriever
from impact_analysis.service import ImpactAnalysisService
from graph_store import Neo4jGraphStore

router = APIRouter(prefix="/api", tags=["Self-RAG"])

# Singleton services
indexer = CodeIndexer(persist_dir="./chroma_db")
store = Neo4jGraphStore()
retriever = HybridRetriever(indexer=indexer, graph_store=store)
impact_service = ImpactAnalysisService(graph_store=store)

qa_service = SelfRAGQAService(hybrid_retriever=retriever)
refactor_service = SelfRAGRefactorService(hybrid_retriever=retriever, impact_service=impact_service, store=store)

@router.post("/qa", response_model=QAResponse)
def ask_codebase(request: QARequest):
    """
    Codebase Question Answering powered by Self-RAG reflection tokens:
    [Retrieve] -> Hybrid Retrieval -> [IsRel] -> LLM Answer -> [IsSup] -> [IsUse]
    """
    try:
        response = qa_service.answer_query(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-RAG QA Error: {str(e)}")

@router.post("/refactor", response_model=RefactorResponse)
def refactor_code(request: RefactorRequest):
    """
    Closed-Loop Code Refactoring powered by Self-RAG and Domino Impact Analysis:
    Retrieves entity -> Generates Diff -> Tree-sitter AST validation -> Domino caller impact check
    """
    try:
        response = refactor_service.refactor(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-RAG Refactor Error: {str(e)}")

@router.get("/self-rag/stats")
def get_stats():
    """
    Health check and index statistics for Self-RAG.
    """
    repos = list(indexer.bm25_indices.keys())
    total_chunks = len(indexer.code_store)
    return {
        "status": "active",
        "indexed_chunks": total_chunks,
        "indexed_repos": repos,
        "total_chunks_indexed": total_chunks,
        "repositories": repos
    }
