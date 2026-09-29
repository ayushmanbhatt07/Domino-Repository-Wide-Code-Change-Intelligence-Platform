# Domino Progress Report

## 1. Where we are
* **Current stage:** Partway through Stage 5 (Change Impact Analysis).
* **Sub-step:** Finished up to 5.2 (Models/Matcher) and 5.5 (Downstream Traversal).
* **What works end to end today:** Given a valid GitHub URL, the backend successfully clones the repository, analyzes Python files to construct a graph (with some flaws), and writes it to a Neo4j database synchronously.
* **Biggest blocker:** `traversal.py` traverses *outgoing* edges (what X depends on) rather than *incoming* edges (what depends on X, i.e., what is impacted). Additionally, `test_impact.py` crashes due to a completely missing `impact_analysis.service` module.

## 2. Stage status table
| Stage | Status | Evidence (file:line) | Notes |
|---|---|---|---|
| 1. Ingestion | PARTIAL | `backend/ingestion.py:63` | Works via GitPython. Missing cleanup of `workspace/` temp folders. |
| 2. Understanding | WORKING BUT BUGGY | `backend/analysis.py:93` | Extracts functions, classes, imports. Bug: `dict.get()` matches as API route. |
| 3. Dependency Graph | WORKING BUT BUGGY | `backend/dependency_graph.py:179` | Maps nodes. Resolves internal calls via simple string matching, ignoring classes/imports. |
| 4. Graph Persistence | WORKING BUT BUGGY | `backend/graph_store.py:46` | Connects to Neo4j. Flaws: N+1 query loop instead of `UNWIND`, no constraints. |
| 5. Impact Analysis | PARTIAL | `backend/impact_analysis/traversal.py:6` | Has models and matcher. `service.py` is missing. Traversal follows outgoing edges only. |
| 6. Engineering Intelligence | NOT STARTED | - | No risk scoring or test recommendation logic exists in the codebase. |
| 7. LLM Explanation | NOT STARTED | - | No LangChain or Gemini API integration code exists. |

## 3. Stage 5 checklist
| Sub-step | Status | File:Line | Justification |
|---|---|---|---|
| 5.1 Request/response models | DONE | `backend/impact_analysis/models.py:6` | `ImpactAnalysisRequest` and `Response` are defined. |
| 5.2 Entity matching | DONE | `backend/impact_analysis/matcher.py:6` | `ImpactMatcher.match()` locates nodes via Neo4j `find_entity`. |
| 5.3 Direct relationship lookup | MISSING | - | No code to fetch immediate incoming+outgoing edges separately. |
| 5.4 Upstream traversal | MISSING | - | `traversal.py` uses `find_downstream` instead of upstream. |
| 5.5 Downstream traversal | DONE | `backend/impact_analysis/traversal.py:6` | Uses `find_downstream` from `graph_store.py`. |
| 5.6 Combine + deduplicate | MISSING | - | No aggregation logic exists. |
| 5.7 Categorize impacted entities | MISSING | - | Nodes are not mapped into grouped sets. |
| 5.8 Record dependency paths | MISSING | - | Only node IDs are returned, not edges/paths. |
| 5.9 Depth control | PARTIAL | `backend/impact_analysis/models.py:14` | Depth exists in model and `find_downstream`, but isn't orchestrated for impact. |
| 5.10 ImpactAnalysisService | MISSING | - | The file `service.py` does not exist, breaking `test_impact.py`. |
| 5.11 POST /impact endpoint | MISSING | - | Not present in `main.py`. |
| 5.12 Tested against Neo4j | MISSING | - | `test_impact.py` crashes; Neo4j is unreachable locally. |
| 5.13-5.17 Entity impacts | MISSING | - | No routing logic handles impacts for files vs routes vs functions. |
| 5.18-5.20 Ambiguous entities | MISSING | - | Code assumes single node match or errors out. |

**Verdict:** We have finished up to 5.2 and are partway through 5.9 (depth control on downstream), but lack the core orchestration service and upstream logic.

## 4. Claim verification table

| ID | Claim | Status | Evidence / Notes |
|---|---|---|---|
| D1 | Route detection uses regex dict .get() calls | **CONFIRMED** | `backend/analysis.py:31` uses `ROUTE_PATTERN.search()`. Output confirms fake routes. |
| D2 | Function node IDs have no class qualifier | **CONFIRMED** | `backend/dependency_graph.py:46` -> `function:{path}:{name}` |
| D3 | Call resolution needs exactly one definition | **CONFIRMED** | `backend/dependency_graph.py:179` returns `matches[0] if len(matches) == 1 else None`. |
| D4 | No IMPORTS edges between files | **CONFIRMED** | They are extracted in `analysis.py` but ignored in `dependency_graph.py`. |
| D5 | External nodes created for local vars | **CONFIRMED** | Output shows `external:source[node.start_byte:node.end_byte].decode`. |
| D6 | `graph_store.py` writes one query at a time | **CONFIRMED** | `backend/graph_store.py:62` loops `tx.run`. |
| D7 | No constraints/indexes on (repo, id) | **CONFIRMED** | Missing in `graph_store.py`. Labels are per-type (File, Function, Class, Route, External), not shared. |
| D8 | `traversal.py` follows outgoing edges | **CONFIRMED** | `backend/graph_store.py:250` uses `(start)-[*1..{depth}]->(n)` which is outgoing. |
| D9 | Cloned repos in workspace/ never cleaned up | **CONFIRMED** | `backend/ingestion.py:63` has no `rmdir` or cleanup logic. |
| D10 | `main.py` writes to `.graphml` unsafely | **CONFIRMED** | `backend/main.py:130` uses a fixed path `graphs/{repo_name}.graphml`. |

## 5. Experiment results
**1. Run `test_impact.py`**
* **Result**: `FAIL`
* **Output**:
```text
Traceback (most recent call last):
  File "D:\Domino-Repository-Wide-Code-Change-Intelligence-Platform\backend\test_impact.py", line 3, in <module>
    from impact_analysis.service import ImpactAnalysisService
ModuleNotFoundError: No module named 'impact_analysis.service'
```

**2. Analyze `backend/` folder locally**
* **Graph Summary**: `{'nodes': 274, 'edges': 385, 'internal_calls': 40, 'external_calls': 215}`
* **Node Types**: `{'file': 26, 'function': 72, 'class': 19, 'route': 33, 'external': 124}`
* **Edge Types**: `{'contains': 91, 'calls': 255, 'handled_by': 39}`
* *(Note: Analyzed via Python script hitting `RepositoryAnalyzer` and `DependencyGraphBuilder` directly).*

**3. Neo4j Read-Only Queries**
* **Result**: Skipped (Not Reachable).
* **Output**:
```text
Testing Neo4j connection...
Neo4j connection failed or unreachable:
neo4j.exceptions.ServiceUnavailable: Couldn't connect to 127.0.0.1:7687
```

## 6. Correctness test
Target function: `function:analysis.py:_text`

**Correct Impacted Set (Callers that depend on this function, meaning if X changes, these break):**
* `function:analysis.py:_name`
* `function:analysis.py:_read_imports`
* `function:analysis.py:_read_routes`
* `function:analysis.py:_callee`

**Actual Traversal Output (using current `traversal.py` logic which uses `(start)-[*1..3]->(n)`):**
* `external:source[node.start_byte:node.end_byte].decode`
**(The code traverses to dependencies of the function rather than those impacted by the function!)*

## 7. Ordered next steps

### Blockers (Must fix before Stage 5 output can be trusted)
1. **Fix Upstream Traversal**
   * *Files*: `backend/graph_store.py`, `backend/impact_analysis/traversal.py`
   * *Change*: Create a `find_upstream` method querying `MATCH (n)<-[*1..depth]-(start)`. Impact analysis requires finding what calls X, not what X calls.
   * *Verification*: Rerun correctness test to ensure callers are returned instead of callees.
2. **Implement ImpactAnalysisService**
   * *Files*: `backend/impact_analysis/service.py`, `backend/test_impact.py`
   * *Change*: Write the missing `ImpactAnalysisService` class to orchestrate the matcher and upstream traversal.
   * *Why before next*: Unblocks `test_impact.py` from crashing and provides the core API for the FastAPI endpoint.
   * *Verification*: `test_impact.py` runs without `ModuleNotFoundError`.
3. **Fix API Route Detection Regex**
   * *Files*: `backend/analysis.py`
   * *Change*: Parse exact AST decorator nodes (`@app.get`) instead of applying a generic regex over all `.get` calls.
   * *Why before next*: Prevents the graph from being flooded with fake route nodes (e.g., standard dictionary lookups).
   * *Verification*: The analyzer outputs 0 routes on the backend codebase.

### Finish Stage 5
4. **Fix Function Name Collisions**
   * *Files*: `backend/dependency_graph.py`
   * *Change*: Resolve calls using class scopes and `import` context rather than rejecting matches when `len(matches) > 1`.
   * *Why before next*: Ensures accurate intra-file links, making the graph complete.
5. **Implement POST `/impact-analysis`**
   * *Files*: `backend/main.py`
   * *Change*: Expose the `ImpactAnalysisService` to users via a standard FastAPI route using the defined `ImpactAnalysisRequest` and `Response` models.

### Then Stage 6 / 7
6. **Implement Risk Scoring & LLM Explanations**
   * *Files*: New `backend/intelligence/` or `backend/llm/` modules.
   * *Change*: Add heuristic graph metrics (e.g., in-degree scoring) and LangChain connections to explain the impacted set.

*Notes on the current plan*: 
* **Drop / Reorder**: I disagree with focusing on advanced LLM reasoning (Stage 7) before fixing the core Neo4j insertion loop (N+1 queries) and `workspace/` temp cleanup (Storage leaks). The LLM will perform poorly if the underlying graph fails to insert properly for medium-to-large repositories due to timeouts, and the disk will rapidly fill up. Optimization and cleanup should be inserted at Stage 4.5.

## 8. Open questions you could not answer from the code
* How are multiple identical function names across different files meant to be resolved without implementing a full type inference engine?
* Should the backend authenticate incoming requests, as the `pipeline.md` implied JWT but the code lacks any authentication?
* Why does the `DependencyGraphBuilder` discard all import statements collected by the `RepositoryAnalyzer`? Are they intended to be used in a later iteration of the code?
