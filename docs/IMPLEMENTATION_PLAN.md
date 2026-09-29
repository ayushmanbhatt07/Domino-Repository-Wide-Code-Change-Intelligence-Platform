# Implementation Plan: Stage 5 & 6 (Impact & Intelligence)

## Phase 0: Fix the Blockers
1. **Fix `graph_store.py` Indentation**: Move the un-indented graph methods inside the `Neo4jGraphStore` class so they actually work (N1).
2. **Path Normalization**: Ensure all node IDs use forward slashes via `Path.as_posix()` (N2).
3. **Stable Repo Identity**: Modify `ingestion.py` and `graph_store.py` to use a repository name (e.g., `owner__name`) derived from the GitHub URL rather than a timestamped path. Extract the `commit_sha`.
4. **Ingestion Hygiene**: Update `ingestion.py` to optionally clean up cloned temp folders via a `keep_clone` flag. Remove the unsafe fixed `.graphml` path write.
5. **AST Analyzer Overhaul (`analysis.py`)**:
   - Extract fully qualified function/method names and class names.
   - Accurately parse imports, handling relative and star imports.
   - Refactor call extraction to use AST dotted names, handling dynamic cases.
   - Re-implement Route detection to strictly parse decorators (like `@app.get` or `@router.post`).
   - Extract FastAPI `Depends(...)` for dependency tracking.
   - Extract type annotations, response_model for references.
   - Recognize HTTP client test calls (`client.get()`).
6. **Dependency Graph Builder Schema (`dependency_graph.py`)**:
   - Map AST entities to strict node IDs (`file:`, `class:`, `function:`, `route:`, `external:`).
   - Resolve edges step-by-step: `self/cls` -> `super` -> `same_file` -> `import` -> `qualified` -> `unique` -> `ambiguous` -> `external`.
7. **Graph Store Persistence (`graph_store.py`)**:
   - Rewrite `save()` to use atomic `UNWIND` batches per node/edge type, replacing the old graph in one transaction.
   - Ensure `(n.repo, n.id)` uniqueness constraints and indexes are created via `ensure_schema()`.

## Phase 1: Stage 5 (Impact Analysis)
1. **Models (`models.py`)**: Create `ImpactAnalysisRequest` and `ImpactAnalysisResponse` using Pydantic, supporting depth limits, confident levels, and detailed result categories.
2. **Matcher (`matcher.py`)**: Accept requests, use graph index lookups to find initial seed nodes. Handle ambiguous names and return close matches for NOT_FOUND scenarios.
3. **Traversal (`traversal.py`)**: Implement BFS (shortest path) fetching edges step-by-step with `neighbors()` queries in Neo4j. Distinguish downstream dependencies vs upstream impact safely.
4. **Service (`service.py`)**: Tie matcher and traversal together. Connect the request to BFS and map output to the response model.
5. **API (`router.py`)**: Implement `POST /impact-analysis`, `GET /repos`, etc., without freezing the event loop.

## Phase 2: Stage 6 (Engineering Intelligence)
1. **Metrics & Hotspots (`metrics.py`, `hotspots.py`)**: Calculate graph-wide fan-in, reverse reach, and hotspot rankings, caching loaded graphs to avoid repetitive reads.
2. **Risk Scoring (`risk.py`)**: Implement a 0-100 heuristic scoring engine utilizing weights for reach, API exposure, depth, hotspots, test gaps, and uncertainty.
3. **Test Recommendation (`test_recommender.py`)**: Find tests matching the impacted sets and rank them by depth/coverage. Flag gaps (untested_impacted).
4. **Reporting (`report.py`)**: Generate comprehensive Markdown and JSON reports.

## Phase 3: Testing
1. **Fixture Upgrades**: Build out `fixtures/sample_repo` to test all OOP, FastAPI, and edge-cases (cycles, syntax errors).
2. **Unit & Neo4j Tests**: Achieve 85%+ coverage on new modules. Prove uniqueness and batching constraints. 
3. **API & End-to-End**: Test endpoint contracts and concurrent limits.
4. **Oracle Evaluation**: Use `ast` stdlib directly to calculate true precision/recall for `fastapi_tutorial` and `Domino` backend itself.

## Phase 4: Documentation
1. Update `README.md`.
2. Write `GRAPH_SCHEMA.md`, `IMPACT_SEMANTICS.md`, `API.md`, `DECISIONS.md`, and `RISK_MODEL.md`.
