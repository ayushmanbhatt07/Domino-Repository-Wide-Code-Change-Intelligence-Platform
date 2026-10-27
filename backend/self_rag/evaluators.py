import os
import json
import re
from typing import List, Dict, Any, Optional
from .models import (
    RetrievalDecision,
    RelevanceCritique,
    GroundingCritique,
    UtilityCritique
)

class SelfRAGEvaluator:
    """
    Self-RAG Evaluator implementing reflection tokens:
    - [Retrieve]: Adaptive Retrieval Gate
    - [IsRel]: Passage Relevance Critique
    - [IsSup]: Factual Grounding & Hallucination Critique
    - [IsUse]: Utility & Completeness Critique
    """
    def __init__(self, llm=None):
        self.llm = llm

    def decide_retrieval(self, query: str) -> RetrievalDecision:
        """
        Determines whether the user's query requires codebase retrieval or can be answered directly.
        Token: [Retrieve] vs [NoRetrieve]
        """
        # Fast heuristic checks
        general_indicators = [
            "what is ", "explain what", "how does python", "difference between", "syntax for"
        ]
        codebase_indicators = [
            "in this repo", "in this project", "endpoint", "route", "function", "class",
            "where is", "how does", "auth", "database", "model", "refactor", "call", "import",
            "test", "controller", "service", ".py", "api", "flow"
        ]

        query_lower = query.lower()
        has_codebase_keyword = any(k in query_lower for k in codebase_indicators)
        has_general_keyword = any(query_lower.startswith(k) for k in general_indicators)

        if has_codebase_keyword or not has_general_keyword:
            return RetrievalDecision(
                needs_retrieval=True,
                decision_token="[Retrieve]",
                rationale="Query requires repository-specific symbols, architecture, or code context."
            )
        else:
            return RetrievalDecision(
                needs_retrieval=False,
                decision_token="[NoRetrieve]",
                rationale="General conceptual question not requiring repository code retrieval."
            )

    def critique_relevance(self, query: str, candidate_chunk: Dict[str, Any]) -> RelevanceCritique:
        """
        Critiques whether a retrieved code chunk is relevant to the query.
        Token: [IsRel] vs [NotRel]
        """
        query_words = set(re.findall(r"\w+", query.lower()))
        code_text = candidate_chunk.get("code", "")
        meta = candidate_chunk.get("metadata", {})
        chunk_text = f"{meta.get('name', '')} {meta.get('qualified_name', '')} {meta.get('file_path', '')} {code_text}".lower()

        overlap = query_words.intersection(set(re.findall(r"\w+", chunk_text)))
        overlap_ratio = len(overlap) / (len(query_words) or 1)

        # High relevance if symbol name or core terms match
        if overlap_ratio >= 0.2 or any(w in meta.get("name", "").lower() for w in query_words if len(w) > 3):
            return RelevanceCritique(
                is_relevant=True,
                relevance_token="[IsRel]",
                relevance_score=min(1.0, 0.5 + overlap_ratio),
                rationale=f"Code chunk matches key query terms: {list(overlap)[:5]}"
            )
        else:
            return RelevanceCritique(
                is_relevant=False,
                relevance_token="[NotRel]",
                relevance_score=overlap_ratio,
                rationale="Code chunk contains minimal keyword overlap with developer query."
            )

    def critique_grounding(self, response_text: str, context_chunks: List[Dict[str, Any]]) -> GroundingCritique:
        """
        Verifies that all symbols, file paths, and function calls generated are supported by context.
        Token: [IsSup] vs [PartSup] vs [NoSup]
        """
        # Collect all valid symbols from context
        context_symbols = set()
        for c in context_chunks:
            meta = c.get("metadata", {})
            if meta.get("name"): context_symbols.add(meta["name"])
            if meta.get("qualified_name"): context_symbols.add(meta["qualified_name"])
            if meta.get("file_path"): context_symbols.add(meta["file_path"])

        # Find mentioned functions or file references in response
        mentioned_symbols = re.findall(r"`([a-zA-Z_][a-zA-Z0-9_\.\/]*)`", response_text)
        hallucinated = []
        for sym in mentioned_symbols:
            # Skip common python builtins
            if sym in {"def", "class", "async", "await", "self", "None", "True", "False", "int", "str", "dict", "list"}:
                continue
            if "." in sym or "_" in sym:
                base = sym.split(".")[-1]
                if not any(base in cs or sym in cs for cs in context_symbols) and len(base) > 4:
                    hallucinated.append(sym)

        hallucinated = list(set(hallucinated))
        if not hallucinated:
            return GroundingCritique(
                is_supported=True,
                grounding_token="[IsSup]",
                hallucinated_symbols=[],
                rationale="All referenced symbols and contracts are grounded in retrieved repository code."
            )
        elif len(hallucinated) <= 2:
            return GroundingCritique(
                is_supported=True,
                grounding_token="[PartSup]",
                hallucinated_symbols=hallucinated,
                rationale=f"Response is mostly grounded, but introduces unverified symbols: {hallucinated}"
            )
        else:
            return GroundingCritique(
                is_supported=False,
                grounding_token="[NoSup]",
                hallucinated_symbols=hallucinated,
                rationale=f"Multiple unsupported symbols detected: {hallucinated}"
            )

    def critique_utility(self, query: str, response_text: str) -> UtilityCritique:
        """
        Scores the utility and actionable quality of the final response.
        Token: [IsUse:1] to [IsUse:5]
        """
        length = len(response_text.strip())
        if length < 30:
            return UtilityCritique(
                utility_score=1,
                utility_token="[IsUse:1]",
                is_acceptable=False,
                feedback="Response is too brief or empty."
            )
        
        has_code_block = "```" in response_text or "def " in response_text
        has_explanation = any(term in response_text.lower() for term in ["because", "impact", "flow", "implements", "file", "path"])

        score = 3
        if has_code_block: score += 1
        if has_explanation: score += 1

        score = min(5, score)
        return UtilityCritique(
            utility_score=score,
            utility_token=f"[IsUse:{score}]",
            is_acceptable=score >= 3,
            feedback=f"Response provides satisfactory utility (Score {score}/5)."
        )
