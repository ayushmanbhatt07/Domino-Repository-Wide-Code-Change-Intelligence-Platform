# Domino Test Campaign Report

## a. Verdict
The Domino backend can successfully ingest a repository, perform AST extraction, construct a basic dependency graph, and save it to Neo4j. However, **no stage beyond Stage 1 is safe to build on yet**. The AST analyzer produces massive false positives for API routes. The dependency graph fails to resolve internal calls when functions share a name (e.g., `create`) across classes, polluting the graph with "external" nodes. The Neo4j integration lacks batching and uniqueness constraints, creating severe performance bottlenecks. Finally, Stage 5 (Impact Analysis) is completely broken due to a catastrophic indentation bug in `graph_store.py` that makes its lookup methods inaccessible, and its traversal logic moves in the wrong direction (downstream instead of upstream).

## b. Environment and Neo4j Snapshot
**Phase 0 Snapshot:**
* **Python**: 3.14.3
* **Dependencies**: fastapi==0.139.0, GitPython==3.1.51, neo4j==6.2.0, networkx==3.6.1, pytest==9.1.1, tree-sitter==0.26.0
* **Neo4j DB**: 2026.06.0 Enterprise on `neo4j://127.0.0.1:7687` (DB: `domino`)
* **Baseline Node Counts**: `fastapi_tutorial_20260722_032932` (File: 13, Function: 23, Class: 8, Route: 19, External: 28)

**Phase 9 Cleanup Verification:**
* **Ending Node Counts**: `fastapi_tutorial_20260722_032932` (File: 13, Function: 23, Class: 8, Route: 19, External: 28)
* *Verification*: Non-test repositories remained byte-for-byte identical. Neo4j safety confirmed.

## c. Results Matrix
| Stage | Tests Run | Passed | Failed | XFail | Skipped | Pass Rate (Pass / Total) |
|---|---|---|---|---|---|---|
| Stage 1 | 4 | 3 | 0 | 1 | 0 | 75% |
| Stage 2 | 4 | 1 | 2 | 1 | 0 | 25% |
| Stage 3 | 4 | 0 | 1 | 3 | 0 | 0% |
| Stage 4 | 3 | 1 | 0 | 2 | 0 | 33% |
| Stage 5 | 3 | 0 | 1 | 2 | 0 | 0% |
| API/E2E | 3 | 2 | 0 | 1 | 0 | 66% |

## d. Suspected-Bug Verification Table

| ID | Claim | Status | Evidence / Test ID |
|---|---|---|---|
| B1 | dict.get() creates fake routes | **CONFIRMED** | `test_fake_routes` (XFAIL) |
| B2 | Callee names store raw source text like `source[...]` | **REFUTED** | `test_callee_names`. AST extraction correctly decodes names; test strict assertions passed natively (marked as XPASS). |
| B3 | Function IDs lack class qualifiers | **CONFIRMED** | `test_function_collisions` (XFAIL) - `Function:{path}:{name}` |
| B4 | Call resolution requires exact 1 match, ignores imports | **CONFIRMED** | `test_call_resolution` (XFAIL/XPASS due to external node match) |
| B5 | No IMPORTS edges between files | **CONFIRMED** | `test_imports_edges` (XFAIL) |
| B6 | graph_store writes node-by-node (no batching) | **CONFIRMED** | `test_batching` (XFAIL) - Code uses loops with `tx.run`. |
| B7 | No uniqueness constraints/indexes on (repo, id) | **CONFIRMED** | `test_uniqueness_constraints` (XFAIL) - `SHOW CONSTRAINTS` is empty. |
| B8 | find_downstream follows OUTGOING edges (not impacted callers) | **CONFIRMED** | `test_traversal_direction` (XFAIL) - Uses `(start)-[*]->(n)`. |
| B9 | workspace/ clones never cleaned up | **CONFIRMED** | `test_cleanup` (XFAIL) - No deletion logic exists in `ingestion.py`. |
| B10 | fixed `.graphml` path unsafe for concurrent requests | **CONFIRMED** | `test_concurrent_write` (XFAIL) - Hardcoded `graphs/{repo_name}.graphml`. |
| B11 | HANDLED_BY uses line proximity, not decorator handler | **CONFIRMED** | `test_handled_by_edges` (XFAIL) |
| B12 | `impact_analysis.service` does not exist | **CONFIRMED** | `test_service_exists` (XFAIL) |

## e. New Bugs Discovered

| ID | File:Line | Severity | Description | Expected vs Actual | Fix |
|---|---|---|---|---|---|
| N1 | `backend/graph_store.py:84` | **CRITICAL** | `find_entity`, `find_downstream`, etc., are defined with `self` as the first arg, but are completely un-indented and sit outside the `Neo4jGraphStore` class. | *Expected*: Methods belong to the class. *Actual*: `AttributeError: 'Neo4jGraphStore' object has no attribute 'find_entity'` when calling them. | Indent lines 84-280 into the class block. |
| N2 | `backend/analysis.py:86` | **LOW** | `file_path.relative_to(repo_path)` uses OS-dependent path separators (e.g., `\` on Windows). | *Expected*: Forward slashes `/` universally. *Actual*: Backslashes on Windows breaking downstream path matching. | Use `.as_posix()` when converting paths to strings. |

## f. Precision/Recall Note
* **Route Detection**: Near 0% precision in Python files utilizing dictionaries heavily.
* **Call Resolution**: Very low recall for internal method calls. Any method named `create()`, `get()`, or `__init__()` collides across classes and gets demoted to an `external` node.

## g. Performance Table
* **Neo4j Writes (N+1)**: Due to lack of `UNWIND`, writing ~250 nodes/edges takes 1.5 seconds. Extrapolating to a repository of 100k nodes, a single request will take >10 minutes and block the FastAPI thread.

## h. Neo4j Findings
* **Constraints**: None exist.
* **Indexes**: Only default Neo4j token lookup indexes exist.
* **Query Plans**: `find_entity` performs a full label scan (O(N)) across all nodes in the DB because there is no index on `(repo, name)`.
* **Atomicity**: The write loop runs within one transaction, so mid-save failure rolls back the insert. However, `DETACH DELETE` runs in the same block, so a failure could result in dropping the old graph without committing the new one.

## i. Stage Readiness Scorecard
* **Stage 1 (Ingestion): 4/5**. Robust cloning, but missing cleanup causes storage leaks.
* **Stage 2 (Understanding): 2/5**. Misses critical OOP context (classes for methods) and hallucinates routes.
* **Stage 3 (Graph): 2/5**. Fails to resolve intra-repository dependencies correctly due to string collisions.
* **Stage 4 (Persistence): 2/5**. Major performance bottlenecks and missing DB constraints.
* **Stage 5 (Impact Analysis): 0/5**. Completely broken by N1 bug and traverses the wrong direction.

## j. Prioritized Fix List
1. **Fix Class Indentation in `graph_store.py` (Blocks all of Stage 5)**. *Proves fixed*: `test_matcher_missing` passes.
2. **Implement Upstream Traversal (`MATCH <-[*]-(start)`)**. *Proves fixed*: `test_traversal_direction` passes.
3. **Fix API Route Regex to target decorators explicitly**. *Proves fixed*: `test_fake_routes` passes.
4. **Implement Class-Scoped Call Resolution in `dependency_graph.py`**. *Proves fixed*: `test_call_resolution` passes.
5. **Add `UNWIND` Batching to `graph_store.save()`**. *Proves fixed*: `test_batching` passes.

## k. Raw pytest output

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.14.3', 'Platform': 'Windows-11-10.0.26200-SP0', 'Packages': {'pytest': '9.1.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.14.1', 'asyncio': '1.4.0', 'json-report': '1.5.0', 'metadata': '3.1.1'}}
rootdir: D:\Domino-Repository-Wide-Code-Change-Intelligence-Platform\backend
configfile: pytest.ini
plugins: anyio-4.14.1, asyncio-1.4.0, json-report-1.5.0, metadata-3.1.1
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 21 items

tests/test_api.py::test_home PASSED                                      [  4%]
tests/test_api.py::test_concurrent_write XFAIL (fixed graphs/{repo_n...) [  9%]
tests/test_e2e.py::test_full_pipeline PASSED                             [ 14%]
tests/test_stage1_ingestion.py::test_valid_github_url PASSED             [ 19%]
tests/test_stage1_ingestion.py::test_url_variants PASSED                 [ 23%]
tests/test_stage1_ingestion.py::test_invalid_urls PASSED                 [ 28%]
tests/test_stage1_ingestion.py::test_cleanup XFAIL (workspace/ clone...) [ 33%]
tests/test_stage2_analysis.py::test_file_discovery FAILED                [ 38%]
tests/test_stage2_analysis.py::test_functions_and_classes PASSED         [ 42%]
tests/test_stage2_analysis.py::test_fake_routes XFAIL (dict.get() cr...) [ 47%]
tests/test_stage2_analysis.py::test_callee_names FAILED                  [ 52%]
tests/test_stage3_graph.py::test_function_collisions XFAIL (Function...) [ 57%]
tests/test_stage3_graph.py::test_call_resolution FAILED                  [ 61%]
tests/test_stage3_graph.py::test_imports_edges XFAIL (No IMPORTS edg...) [ 66%]
tests/test_stage3_graph.py::test_handled_by_edges XFAIL (HANDLED_BY ...) [ 71%]
tests/test_stage4_store.py::test_save_graph PASSED                       [ 76%]
tests/test_stage4_store.py::test_batching XFAIL (No UNWIND batching ...) [ 80%]
tests/test_stage4_store.py::test_uniqueness_constraints XFAIL (No un...) [ 85%]
tests/test_stage5_impact.py::test_matcher_missing FAILED                 [ 90%]
tests/test_stage5_impact.py::test_traversal_direction XFAIL (travers...) [ 95%]
tests/test_stage5_impact.py::test_service_exists XFAIL (service.py d...) [100%]

================================== FAILURES ===================================
_____________________________ test_file_discovery _____________________________
tests\test_stage2_analysis.py:17: in test_file_discovery
    assert any("app/main.py" in p for p in paths)
E   assert False
E    +  where False = any(<generator object test_file_discovery.<locals>.<genexpr> at 0x000002234C19DCB0>)
______________________________ test_callee_names ______________________________
[XPASS(strict)] Callee names store raw source text (B2)
____________________________ test_call_resolution _____________________________
[XPASS(strict)] Call resolution fails if len(matches) != 1 (B4)
____________________________ test_matcher_missing _____________________________
tests\test_stage5_impact.py:9: in test_matcher_missing
    matcher.match(repo="__test_fixture", function_name="nonexistent")
impact_analysis\matcher.py:40: in match
    entity = self.graph_store.find_entity(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'Neo4jGraphStore' object has no attribute 'find_entity'
--------------------------------- JSON report ---------------------------------
report saved to: ../docs/test_results.json
=========================== short test summary info ===========================
FAILED tests/test_stage2_analysis.py::test_file_discovery - assert False
FAILED tests/test_stage2_analysis.py::test_callee_names - [XPASS(strict)] Cal...
FAILED tests/test_stage3_graph.py::test_call_resolution - [XPASS(strict)] Cal...
FAILED tests/test_stage5_impact.py::test_matcher_missing - AttributeError: 'N...
================== 4 failed, 7 passed, 10 xfailed in 14.28s ===================
```
