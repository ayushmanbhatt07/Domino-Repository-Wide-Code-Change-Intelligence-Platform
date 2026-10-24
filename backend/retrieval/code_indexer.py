import os
import hashlib
import math
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from typing import Dict, Any, List, Optional
from .bm25 import BM25Index

class LocalFeatureEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Deterministic offline semantic code embedding function.
    Eliminates external remote downloads while preserving semantic vector similarity.
    """
    def __init__(self, dim: int = 128):
        self.dim = dim

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            vec = [0.0] * self.dim
            words = text.lower().split()
            for w in words:
                h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % self.dim
                vec[h] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            embeddings.append([x / norm for x in vec])
        return embeddings

    def name(self) -> str:
        return "local_feature_embedding"

class CodeIndexer:
    """
    Indexes repository source code chunks into both ChromaDB (Dense Vector Store)
    and BM25 (Sparse Keyword Store).
    """
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.persist_dir = persist_dir
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.embedding_fn = LocalFeatureEmbeddingFunction(dim=128)
        self.bm25_indices: Dict[str, BM25Index] = {}
        self.code_store: Dict[str, Dict[str, Any]] = {} # chunk_id -> chunk_data

    def index_repository(self, repo_id: str, analysis_result: Dict[str, Any]) -> int:
        """
        Extracts semantic code chunks (functions, classes, routes) and indexes them.
        """
        collection_name = f"repo_{repo_id.replace('-', '_').replace('/', '_')}"
        # Delete if exists to refresh
        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass

        collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"repo_id": repo_id}
        )

        documents_for_bm25 = []
        ids = []
        documents = []
        metadatas = []

        files = analysis_result.get("files", [])
        for file_info in files:
            file_path = file_info.get("path", "")
            
            # 1. Index functions
            for fn in file_info.get("functions", []):
                chunk_id = f"{file_path}::{fn.get('qualified_name', fn.get('name'))}"
                code = fn.get("code_content", "")
                if not code:
                    code = f"def {fn.get('name')}():\n    pass # lines {fn.get('start_line')}-{fn.get('end_line')}"
                
                meta = {
                    "type": "function",
                    "name": fn.get("name", ""),
                    "qualified_name": fn.get("qualified_name", ""),
                    "file_path": file_path,
                    "start_line": int(fn.get("start_line", 1)),
                    "end_line": int(fn.get("end_line", 1)),
                    "is_test": bool(fn.get("is_test", False)),
                    "repo_id": repo_id
                }
                
                self.code_store[chunk_id] = {
                    "id": chunk_id,
                    "code": code,
                    "metadata": meta
                }
                
                ids.append(chunk_id)
                documents.append(f"Function: {fn.get('qualified_name')}\nFile: {file_path}\n{code}")
                metadatas.append(meta)
                documents_for_bm25.append({"id": chunk_id, "content": f"{fn.get('name')} {fn.get('qualified_name')} {code}", "metadata": meta})

            # 2. Index classes
            for cls in file_info.get("classes", []):
                chunk_id = f"{file_path}::{cls.get('qualified_name', cls.get('name'))}"
                code = cls.get("code_content", "")
                if not code:
                    code = f"class {cls.get('name')}:\n    pass # lines {cls.get('start_line')}-{cls.get('end_line')}"
                
                meta = {
                    "type": "class",
                    "name": cls.get("name", ""),
                    "qualified_name": cls.get("qualified_name", ""),
                    "file_path": file_path,
                    "start_line": int(cls.get("start_line", 1)),
                    "end_line": int(cls.get("end_line", 1)),
                    "is_test": bool(cls.get("is_test", False)),
                    "repo_id": repo_id
                }
                
                self.code_store[chunk_id] = {
                    "id": chunk_id,
                    "code": code,
                    "metadata": meta
                }
                
                ids.append(chunk_id)
                documents.append(f"Class: {cls.get('qualified_name')}\nFile: {file_path}\n{code}")
                metadatas.append(meta)
                documents_for_bm25.append({"id": chunk_id, "content": f"{cls.get('name')} {cls.get('qualified_name')} {code}", "metadata": meta})

        # Add to ChromaDB in batches
        if ids:
            batch_size = 50
            for i in range(0, len(ids), batch_size):
                collection.add(
                    ids=ids[i:i+batch_size],
                    documents=documents[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size]
                )

        # Build BM25
        bm25 = BM25Index()
        bm25.build_index(documents_for_bm25)
        self.bm25_indices[repo_id] = bm25

        return len(ids)

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        return self.code_store.get(chunk_id)
