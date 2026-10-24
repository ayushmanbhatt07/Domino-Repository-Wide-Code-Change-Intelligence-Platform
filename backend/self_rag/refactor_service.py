import difflib
from typing import Dict, Any, List, Optional
from parser_utils import get_python_parser
from .models import (
    RefactorRequest,
    RefactorResponse,
    ReflectionTrace,
    RetrievalDecision
)
from .evaluators import SelfRAGEvaluator
from retrieval.hybrid_retriever import HybridRetriever
from impact_analysis.service import ImpactAnalysisService
from impact_analysis.models import ImpactAnalysisRequest
from intelligence.test_recommender import TestRecommender
from intelligence.metrics import GraphMetricsCache
from ai_reasoning.llm_service import LLMService

class SelfRAGRefactorService:
    """
    Closed-Loop Refactoring Assistant based on Self-RAG and Domino Impact Analysis.
    Workflow:
    1. Retrieval: Fetch target entity and callers
    2. Generation: Produce refactored code diff
    3. Syntax Verification: Tree-sitter validates AST correctness
    4. Domino Impact Verification: Traces downstream callers, routes, and tests
    5. Ripple Updates: Generates corresponding caller diffs
    6. Self-Reflection: Evaluates grounding [IsSup] and utility [IsUse]
    """
    def __init__(self, hybrid_retriever: HybridRetriever, impact_service: ImpactAnalysisService, store, llm_service: Optional[LLMService] = None):
        self.retriever = hybrid_retriever
        self.impact_service = impact_service
        self.store = store
        self.llm_service = llm_service or LLMService()
        self.evaluator = SelfRAGEvaluator()
        self.metrics_cache = GraphMetricsCache(store)
        self.test_rec = TestRecommender(self.metrics_cache)
        self.ts_parser = get_python_parser()

    def validate_syntax(self, code_str: str) -> tuple[bool, Optional[str]]:
        """
        Validates Python syntax using Tree-sitter.
        """
        try:
            tree = self.ts_parser.parse(code_str.encode("utf-8"))
            if tree.root_node.has_error:
                # Find syntax error node
                def find_error(n):
                    if n.type == "ERROR": return n
                    for c in n.children:
                        res = find_error(c)
                        if res: return res
                    return None
                err = find_error(tree.root_node)
                line = (err.start_point[0] + 1) if err else "unknown"
                return False, f"Tree-sitter syntax error near line {line}"
            return True, None
        except Exception as e:
            return False, f"Parser exception: {e}"

    def refactor(self, request: RefactorRequest) -> RefactorResponse:
        repo_id = request.repo_id
        target = request.target_entity
        instructions = request.instructions

        trace = ReflectionTrace(
            retrieval_decision=RetrievalDecision(
                needs_retrieval=True,
                decision_token="[Retrieve]",
                rationale="Refactoring requires exact entity source code and caller relationships."
            )
        )

        # 1. Retrieve target code chunk
        target_chunk = self.retriever.indexer.get_chunk(target)
        original_code = target_chunk["code"] if target_chunk else f"# Target: {target}\ndef placeholder(): pass"
        meta = target_chunk.get("metadata", {}) if target_chunk else {}

        # 2. Generate Refactored Code
        prompt = (
            f"You are a refactoring engine. Refactor the following Python code according to the instructions.\n"
            f"Instructions: {instructions}\n\n"
            f"Original Code:\n{original_code}\n\n"
            f"Return ONLY the updated Python code block without Markdown fences or extra commentary."
        )

        proposed_code = ""
        if self.llm_service and self.llm_service.llm:
            try:
                res = self.llm_service.llm.invoke(prompt)
                proposed_code = res.content.strip().replace("```python", "").replace("```", "").strip()
            except Exception:
                pass

        if not proposed_code:
            # Deterministic fallback refactoring example (e.g. async wrapper or type annotations)
            lines = original_code.splitlines()
            if lines and "def " in lines[0] and not lines[0].strip().startswith("async "):
                proposed_code = original_code.replace("def ", "async def ", 1)
            else:
                proposed_code = f"# Refactored with: {instructions}\n" + original_code

        # 3. Tree-sitter Syntax Validation
        is_valid, syntax_err = self.validate_syntax(proposed_code)

        # 4. Compute Unified Diff
        orig_lines = original_code.splitlines(keepends=True)
        new_lines = proposed_code.splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(orig_lines, new_lines, fromfile=f"a/{meta.get('file_path', 'target.py')}", tofile=f"b/{meta.get('file_path', 'target.py')}"))

        # 5. Domino Impact Analysis (Verify Downstream Ripple Effects!)
        target_name = meta.get("name") or (target.split("::")[-1] if "::" in target else target)
        impact_req = ImpactAnalysisRequest(
            repo=repo_id,
            file_name=meta.get("file_path"),
            function_name=target_name,
            depth=3
        )
        impact_res = self.impact_service.analyze(impact_req)

        impacted_callers = len(impact_res.impacted.functions) if impact_res.impacted else 0
        impacted_routes = [r.name for r in impact_res.impacted.routes] if impact_res.impacted else []

        all_impacted_ids = []
        if impact_res.impacted:
            for g in (impact_res.impacted.files, impact_res.impacted.functions, impact_res.impacted.classes, impact_res.impacted.routes):
                all_impacted_ids.extend([e.id for e in g])

        test_data = self.test_rec.recommend(repo_id, all_impacted_ids)
        recommended_tests = test_data.get("recommended_tests", [])

        # 6. Generate Caller Diffs (Ripple Updates)
        caller_diffs = {}
        if impact_res.impacted and impact_res.impacted.functions:
            for f in impact_res.impacted.functions[:3]:
                caller_chunk = self.retriever.indexer.get_chunk(f"{f.file}::{f.name}")
                if caller_chunk:
                    old_c = caller_chunk["code"]
                    # If target converted to async, caller should await it
                    new_c = old_c.replace(f"{target_name}(", f"await {target_name}(")
                    if new_c != old_c:
                        c_diff = "".join(difflib.unified_diff(old_c.splitlines(keepends=True), new_c.splitlines(keepends=True), fromfile=f"a/{f.file}", tofile=f"b/{f.file}"))
                        caller_diffs[f"{f.file}::{f.name}"] = c_diff

        # 7. Self-RAG Critiques: Grounding [IsSup] & Utility [IsUse]
        trace.grounding_critique = self.evaluator.critique_grounding(proposed_code, [target_chunk] if target_chunk else [])
        trace.utility_critique = self.evaluator.critique_utility(instructions, proposed_code)

        return RefactorResponse(
            target_entity=target,
            proposed_code=proposed_code,
            diff=diff,
            syntax_valid=is_valid,
            syntax_error=syntax_err,
            impacted_callers_count=impacted_callers,
            impacted_routes=impacted_routes,
            recommended_tests=recommended_tests,
            caller_diffs=caller_diffs,
            reflection_trace=trace
        )
