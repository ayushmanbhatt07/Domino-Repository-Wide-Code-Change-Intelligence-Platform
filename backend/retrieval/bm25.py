import math
import re
from typing import List, Dict, Any, Tuple

def tokenize_code(text: str) -> List[str]:
    """
    Tokenizes source code by breaking down camelCase, snake_case, symbols, and keywords.
    """
    if not text:
        return []
    # Replace non-alphanumeric with space
    cleaned = re.sub(r"[^a-zA-Z0-9_]", " ", text)
    tokens = []
    for word in cleaned.split():
        # Split snake_case
        parts = word.split("_")
        for part in parts:
            if not part:
                continue
            # Split camelCase
            subparts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+", part)
            if subparts:
                tokens.extend([sp.lower() for sp in subparts])
            else:
                tokens.append(part.lower())
        tokens.append(word.lower())
    return [t for t in tokens if len(t) > 1]

class BM25Index:
    """
    Okapi BM25 Lexical Search Index tailored for Code Repositories.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_ids: List[str] = []
        self.doc_lengths: List[int] = []
        self.doc_metadata: Dict[str, Dict[str, Any]] = {}
        self.avg_doc_len: float = 0.0
        self.inverted_index: Dict[str, Dict[int, int]] = {} # token -> {doc_idx: freq}
        self.idf: Dict[str, float] = {}

    def build_index(self, documents: List[Dict[str, Any]]):
        """
        Builds the BM25 index from a list of documents.
        Each doc must have: {"id": str, "content": str, "metadata": dict}
        """
        self.doc_ids = []
        self.doc_lengths = []
        self.doc_metadata = {}
        self.inverted_index = {}
        total_len = 0

        for idx, doc in enumerate(documents):
            doc_id = doc["id"]
            content = doc.get("content", "")
            self.doc_ids.append(doc_id)
            self.doc_metadata[doc_id] = doc.get("metadata", {})

            tokens = tokenize_code(content)
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_len += doc_len

            # Term frequencies in this document
            tf: Dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1

            for token, freq in tf.items():
                if token not in self.inverted_index:
                    self.inverted_index[token] = {}
                self.inverted_index[token][idx] = freq

        num_docs = len(self.doc_ids)
        self.avg_doc_len = (total_len / num_docs) if num_docs > 0 else 0.0

        # Compute IDF
        self.idf = {}
        for token, postings in self.inverted_index.items():
            df = len(postings)
            # Standard Lucene/BM25 IDF formula with smoothing
            self.idf[token] = math.log(1.0 + (num_docs - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Scores and ranks documents for a search query.
        """
        if not self.doc_ids:
            return []

        query_tokens = tokenize_code(query)
        scores: Dict[int, float] = {}

        for token in query_tokens:
            if token not in self.inverted_index:
                continue
            idf_val = self.idf[token]
            postings = self.inverted_index[token]

            for doc_idx, freq in postings.items():
                doc_len = self.doc_lengths[doc_idx]
                numerator = freq * (self.k1 + 1.0)
                denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0)))
                bm25_term = idf_val * (numerator / denominator)
                scores[doc_idx] = scores.get(doc_idx, 0.0) + bm25_term

        # Sort descending by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for doc_idx, score in ranked:
            doc_id = self.doc_ids[doc_idx]
            results.append({
                "id": doc_id,
                "score": float(score),
                "metadata": self.doc_metadata.get(doc_id, {})
            })
        return results
