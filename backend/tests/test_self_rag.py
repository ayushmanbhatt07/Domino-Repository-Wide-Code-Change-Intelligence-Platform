import pytest
from fastapi.testclient import TestClient
from retrieval.bm25 import BM25Index, tokenize_code
from retrieval.code_indexer import CodeIndexer
from retrieval.hybrid_retriever import HybridRetriever
from self_rag.evaluators import SelfRAGEvaluator
from self_rag.qa_service import SelfRAGQAService
from self_rag.refactor_service import SelfRAGRefactorService
from self_rag.models import QARequest, RefactorRequest
from main import app

client = TestClient(app)

SAMPLE_ANALYSIS = {
    "files": [
        {
            "path": "app/auth.py",
            "functions": [
                {
                    "name": "verify_jwt_token",
                    "qualified_name": "app.auth.verify_jwt_token",
                    "start_line": 10,
                    "end_line": 20,
                    "code_content": "def verify_jwt_token(token: str):\n    # validates token\n    return {'user_id': 123}",
                    "is_test": False
                }
            ],
            "classes": []
        },
        {
            "path": "app/db.py",
            "functions": [
                {
                    "name": "get_db",
                    "qualified_name": "app.db.get_db",
                    "start_line": 5,
                    "end_line": 15,
                    "code_content": "def get_db():\n    db = SessionLocal()\n    try:\n        yield db\n    finally:\n        db.close()",
                    "is_test": False
                }
            ],
            "classes": []
        }
    ]
}

def test_tokenize_code():
    tokens = tokenize_code("def get_database_session(userAuthToken):")
    assert "get" in tokens
    assert "database" in tokens
    assert "session" in tokens
    assert "user" in tokens
    assert "auth" in tokens

def test_bm25_index():
    bm25 = BM25Index()
    docs = [
        {"id": "doc1", "content": "def authenticate_user(token): return True", "metadata": {}},
        {"id": "doc2", "content": "def query_database(): return []", "metadata": {}}
    ]
    bm25.build_index(docs)
    results = bm25.search("authenticate token")
    assert len(results) > 0
    assert results[0]["id"] == "doc1"

def test_code_indexer_and_hybrid_retriever():
    indexer = CodeIndexer(persist_dir="./test_chroma_db")
    count = indexer.index_repository("test_repo", SAMPLE_ANALYSIS)
    assert count == 2

    retriever = HybridRetriever(indexer=indexer)
    results = retriever.retrieve("test_repo", "verify jwt token", top_k=2)
    assert len(results) > 0
    assert "verify_jwt_token" in results[0]["id"]

def test_self_rag_evaluators():
    evaluator = SelfRAGEvaluator()

    # 1. [Retrieve] Decision
    dec1 = evaluator.decide_retrieval("Where is the JWT token verified in this repo?")
    assert dec1.needs_retrieval is True
    assert dec1.decision_token == "[Retrieve]"

    dec2 = evaluator.decide_retrieval("What is a Python generator?")
    assert dec2.needs_retrieval is False
    assert dec2.decision_token == "[NoRetrieve]"

    # 2. [IsRel] Relevance
    chunk = {"code": "def verify_jwt_token(): pass", "metadata": {"name": "verify_jwt_token"}}
    rel = evaluator.critique_relevance("verify jwt", chunk)
    assert rel.is_relevant is True
    assert rel.relevance_token == "[IsRel]"

    # 3. [IsSup] Grounding
    sup = evaluator.critique_grounding("We use `verify_jwt_token` in `app/auth.py`.", [chunk])
    assert sup.is_supported is True
    assert sup.grounding_token in ("[IsSup]", "[PartSup]")

    # 4. [IsUse] Utility
    use = evaluator.critique_utility("how to auth?", "Here is the code block:\n```python\ndef auth(): pass\n```\nBecause it implements token check.")
    assert use.is_acceptable is True
    assert use.utility_score >= 3

def test_qa_service_flow():
    indexer = CodeIndexer(persist_dir="./test_chroma_db")
    indexer.index_repository("test_repo", SAMPLE_ANALYSIS)
    retriever = HybridRetriever(indexer=indexer)
    qa_service = SelfRAGQAService(hybrid_retriever=retriever)

    req = QARequest(repo_id="test_repo", query="Where is the JWT verification handled?")
    res = qa_service.answer_query(req)

    assert res.query == req.query
    assert len(res.citations) > 0
    assert res.reflection_trace.retrieval_decision.decision_token == "[Retrieve]"
    assert res.reflection_trace.grounding_critique is not None

def test_refactor_syntax_validation():
    from parser_utils import get_python_parser
    parser = get_python_parser()
    tree_valid = parser.parse(b"async def foo():\n    return 42\n")
    assert tree_valid.root_node.has_error is False

    tree_invalid = parser.parse(b"def broken_syntax(\n")
    assert tree_invalid.root_node.has_error is True

def test_api_qa_and_stats_endpoints():
    # Test Stats endpoint
    stats_res = client.get("/api/self-rag/stats")
    assert stats_res.status_code == 200
    assert "status" in stats_res.json()

    # Ingest sample into indexer via analyze or direct indexer
    from self_rag.router import indexer
    indexer.index_repository("demo_repo", SAMPLE_ANALYSIS)

    qa_payload = {
        "repo_id": "demo_repo",
        "query": "Where is get_db defined?",
        "top_k": 2
    }
    qa_res = client.post("/api/qa", json=qa_payload)
    assert qa_res.status_code == 200
    data = qa_res.json()
    assert "answer" in data
    assert "reflection_trace" in data
    assert data["reflection_trace"]["retrieval_decision"]["decision_token"] == "[Retrieve]"
