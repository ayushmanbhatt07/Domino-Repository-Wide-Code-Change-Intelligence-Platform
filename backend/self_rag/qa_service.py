import os
from typing import List, Dict, Any, Optional
from .models import (
    QARequest,
    QAResponse,
    ReflectionTrace
)
from .evaluators import SelfRAGEvaluator
from retrieval.hybrid_retriever import HybridRetriever
from ai_reasoning.llm_service import LLMService

class SelfRAGQAService:
    """
    Codebase Question Answering service powered by the Self-RAG loop.
    Workflow:
    1. [Retrieve] Decision -> Decide if codebase context is needed
    2. Hybrid Retrieval -> Vector + BM25 + Domino Graph
    3. [IsRel] Critique -> Filter irrelevant snippets
    4. Code Generation -> Grounded technical explanation
    5. [IsSup] Critique -> Verify factual consistency and detect hallucinations
    6. [IsUse] Critique -> Assess utility and actionable quality
    """
    def __init__(self, hybrid_retriever: HybridRetriever, llm_service: Optional[LLMService] = None):
        self.retriever = hybrid_retriever
        self.llm_service = llm_service or LLMService()
        self.evaluator = SelfRAGEvaluator()

    def answer_query(self, request: QARequest) -> QAResponse:
        repo_id = request.repo_id
        query = request.query
        
        # 1. [Retrieve] Token: Adaptive Retrieval Decision
        decision = self.evaluator.decide_retrieval(query)
        trace = ReflectionTrace(retrieval_decision=decision)

        if not decision.needs_retrieval:
            # Direct response without codebase retrieval
            direct_ans = f"This is a conceptual question answered directly without repository retrieval:\n\n{query}\n\nKey Concepts:\n- Standard architectural pattern applies."
            if self.llm_service and self.llm_service.llm:
                try:
                    res = self.llm_service.llm.invoke(f"Answer this general software development question clearly:\n{query}")
                    direct_ans = res.content
                except Exception:
                    pass
            trace.utility_critique = self.evaluator.critique_utility(query, direct_ans)
            return QAResponse(query=query, answer=direct_ans, citations=[], reflection_trace=trace)

        # 2. Hybrid Retrieval
        candidates = self.retriever.retrieve(repo_id, query, top_k=request.top_k, expand_graph=True)

        # 3. [IsRel] Token: Relevance Critique
        relevant_candidates = []
        for cand in candidates:
            crit = self.evaluator.critique_relevance(query, cand)
            trace.relevance_critiques.append({
                "chunk_id": cand["id"],
                "token": crit.relevance_token,
                "score": crit.relevance_score,
                "rationale": crit.rationale
            })
            if crit.is_relevant or not request.enable_reflection:
                relevant_candidates.append(cand)

        # Fallback if all were rejected: use top-1 candidate to avoid empty context
        if not relevant_candidates and candidates:
            relevant_candidates = [candidates[0]]

        # Build Context Prompt
        context_blocks = []
        citations = []
        for cand in relevant_candidates:
            meta = cand["metadata"]
            code = cand["code"]
            graph_ctx = cand.get("graph_context", {})
            callers_str = ", ".join(graph_ctx.get("callers", [])) or "None"
            callees_str = ", ".join(graph_ctx.get("callees", [])) or "None"

            context_blocks.append(
                f"--- File: {meta.get('file_path')} | Symbol: {meta.get('qualified_name')} (Lines {meta.get('start_line')}-{meta.get('end_line')}) ---\n"
                f"Callers: {callers_str}\n"
                f"Callees: {callees_str}\n"
                f"Code:\n{code}\n"
            )
            citations.append({
                "file": meta.get("file_path"),
                "symbol": meta.get("qualified_name"),
                "lines": f"{meta.get('start_line')}-{meta.get('end_line')}",
                "type": meta.get("type")
            })

        full_context = "\n".join(context_blocks)
        
        # 4. Generation
        prompt = (
            f"You are an expert codebase assistant. Answer the developer's question using the retrieved code context below.\n"
            f"Be precise, cite specific file paths and line numbers, and trace call hierarchies when relevant.\n\n"
            f"Developer Question: {query}\n\n"
            f"Retrieved Code Context:\n{full_context}\n\n"
            f"Answer:"
        )

        answer = ""
        if self.llm_service and self.llm_service.llm:
            try:
                res = self.llm_service.llm.invoke(prompt)
                answer = res.content
            except Exception as e:
                answer = f"Error invoking LLM: {e}\n\nFallback Analysis:\nFound relevant code in {', '.join(c['symbol'] for c in citations)}."
        else:
            # Deterministic fallback when LLM API key is not configured
            answer = (
                f"Analysis for query: '{query}'\n\n"
                f"Relevant Code Sections Found in Repository:\n"
            )
            for c in citations:
                answer += f"- `{c['symbol']}` in `{c['file']}` (Lines {c['lines']})\n"
            answer += f"\nGraph Context & Call Flow:\n{full_context}"

        # 5. [IsSup] Token: Grounding / Hallucination Critique
        grounding = self.evaluator.critique_grounding(answer, relevant_candidates)
        trace.grounding_critique = grounding

        # 6. [IsUse] Token: Utility Critique
        utility = self.evaluator.critique_utility(query, answer)
        trace.utility_critique = utility

        return QAResponse(
            query=query,
            answer=answer,
            citations=citations,
            reflection_trace=trace
        )
