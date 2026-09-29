# Domino Codebase Audit Report

## 1. Executive Summary
Domino is a partially implemented code change intelligence platform consisting of a Python/FastAPI backend, AST-based repository analysis, and Neo4j graph storage. Its biggest strength is a clear architectural vision and a solid graph schema foundation that correctly maps the relationship between files, functions, and classes. However, the system presents significant risks: critical parsing bugs in the AST analyzer (e.g., classifying `dict.get()` as an API route), a fragile and naive function call resolution algorithm that misses many internal calls, and the complete absence of impact analysis logic (reverse dependency traversal). Currently, the codebase is a proof-of-concept rather than a production-ready system.

## 2. Repository Tree and Dependencies
**Dependencies (`backend/requirements.txt`)**:
`fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv`, `gitpython`, `tree-sitter`, `tree-sitter-language-pack`, `neo4j`, `networkx`, `sqlalchemy`, `python-multipart`, `requests`, `rich`, `loguru`.

**Repository Structure (with line counts)**:
```text
/
├── .gitignore (5016 bytes)
├── LICENSE (1093 bytes)
├── README.md (489 lines)
├── pipeline.md (98 lines)
├── docs/ (empty)
├── frontend/ (empty)
└── backend/
    ├── .env / .env.example
    ├── analysis.py (191 lines)
    ├── config.py (11 lines)
    ├── dependency_graph.py (231 lines)
    ├── graph_store.py (279 lines)
    ├── ingestion.py (89 lines)
    ├── main.py (167 lines)
    ├── requirements.txt (24 lines)
    ├── requirements-lock.txt (1638 bytes)
    ├── test_impact.py (26 lines)
    ├── impact_analysis/
    │   ├── matcher.py (52 lines)
    │   ├── models.py (30 lines)
    │   └── traversal.py (16 lines)
    └── workspace/ (contains cloned repos)
```

## 3. Module-by-Module Analysis

* **`analysis.py`**
  * **Purpose**: Parses cloned repositories using tree-sitter AST to extract functions, classes, imports, and routes.
  * **Public API**: `RepositoryAnalyzer().analyze(repo_path)`.
  * **Deep Dive**: Finds all nodes for functions, classes, and calls. Call names are recorded using the AST's `function` or `name` fields (meaning `foo.bar()` records just `bar` or `foo.bar` depending on language/grammar). It detects API routes naively using a regex `.search()` for `.get(`, `.post(`, etc. on all `call` strings. 
  * **Mishandles**: The route regex matches dictionary `.get()` calls, leading to massive false positives. It silently ignores async definitions, decorators, and class inheritance structures.

* **`dependency_graph.py`**
  * **Purpose**: Converts the extracted AST dictionary into a NetworkX DiGraph.
  * **Public API**: `DependencyGraphBuilder().build(analysis)`, `.summary()`, `.export_graphml()`.
  * **Deep Dive**: Edges flow from `file` to `function`/`class` (CONTAINS), `route` to `function` (HANDLED_BY), and `function` to `function` (CALLS). 
  * **Resolution Algorithm**: Checks if the called name (stripping `self.` if present) matches exactly *one* definition in the entire repository. If there are multiple functions with the same name (e.g., `init()` in different files or classes), `len(matches) == 1` fails, and the call is marked as an `external` node. It completely ignores `import` namespaces. Yes, two methods with the same name in different classes collide into separate nodes properly (using ID `function:path:name`), but *calls* to them will fail to resolve. There are **no IMPORTS edges** between files.

* **`graph_store.py`**
  * **Purpose**: Saves the graph to Neo4j.
  * **Public API**: `Neo4jGraphStore().save(repo, graph)`, `find_entity()`, `find_downstream()`.
  * **Deep Dive**: Uses `GraphDatabase.driver` with env vars. Overwrites previous runs using `MATCH (n {repo: $repo}) DETACH DELETE n`. There are no visible uniqueness constraints or indexes defined in the code. Writes are done naively in a loop (`tx.run` for each node/edge individually) rather than using `UNWIND` for batching, which will perform poorly on large repos.

* **`main.py`**
  * **Purpose**: FastAPI entry point.
  * **Public API**: `POST /ingest` (clones repo), `POST /analyze` (runs analysis, builds graph, saves to DB).
  * **Deep Dive**: Glues the pipeline together. Contains blocking operations (cloning, analyzing, and saving to DB run synchronously in the request). Hardcodes `graphs/{repo_name}.graphml` storage, meaning concurrent requests for the same repo will cause file race conditions.

* **`ingestion.py`**
  * **Purpose**: Clones Git repositories into a local `workspace/` directory.
  * **Public API**: `RepositoryIngestionService().ingest(url)`.
  * **Deep Dive**: Validates the URL is github.com, checks HTTP 200, and clones using GitPython to a timestamped folder. **Errors**: Temporary directories are never cleaned up, creating a space leak.

## 4. Graph Schema Reference

| Entity | Neo4j Label | Node ID Format | Properties |
|--------|-------------|----------------|------------|
| File | `File` | `file:{path}` | `repo`, `id`, `name`, `type` |
| Function | `Function` | `function:{path}:{name}` | `repo`, `id`, `name`, `type`, `start_line`, `end_line` |
| Class | `Class` | `class:{path}:{name}` | `repo`, `id`, `name`, `type` |
| Route | `Route` | `route:{METHOD}:{path}` | `repo`, `id`, `method`, `path`, `type` |
| External | `External` | `external:{call_name}` | `repo`, `id`, `name`, `type` |

| Source | Edge Type (Relation) | Target | Note |
|--------|----------------------|--------|------|
| File | `CONTAINS` | Function / Class | A file contains entities |
| Route | `HANDLED_BY` | Function | Route maps to the function right below it |
| Function | `CALLS` | Function / External | Code execution flow |

## 5. Real Experiment Results
Ran the analyzer against `backend/` itself (ignoring `workspace/` and `__pycache__`):
* **Nodes**: 260 total (24 files, 70 functions, 19 classes, 33 routes, 114 external entities)
* **Edges**: 355 total (89 contains, 227 calls, 39 handled_by)
* **Call Resolution**: 35 internal calls resolved successfully, while 192 call edges were marked external.
* **False Positives**: 33 routes were detected! (e.g., `f.get('functions')` in Python was matched by the regex as a `GET /functions` API route).
* **Sample Unresolved Calls (that should be internal/resolved)**: `f.get`, `file_path.read_bytes`, `found.extend`, `get_parser(language).parse`, `ROUTE_PATTERN.search`.

## 6. Findings Table

| ID | File:Line | Severity | Description | Suggested Fix |
|---|---|---|---|---|
| 1 | `backend/analysis.py:31` | High | Route pattern regex (`\.(get\|post...)`) blindly catches standard Python dictionary methods (e.g. `dict.get()`), resulting in massive false-positive routes. | Use tree-sitter to specifically target decorator nodes (e.g. `@app.get(...)`) instead of generic string regex on calls. |
| 2 | `backend/dependency_graph.py:179` | High | Call resolution fails if multiple functions share the same name (`len(matches) == 1`). | Implement namespace/import-aware resolution. Track class ownership for methods and imported aliases. |
| 3 | `backend/graph_store.py:62` | Medium | Node and Edge creation is performed in a Python `for` loop, firing a separate Cypher query for every single node and edge (N+1 query problem). | Refactor to pass lists of dictionaries to Neo4j and use `UNWIND $nodes AS node MERGE ...` for bulk inserts. |
| 4 | `backend/ingestion.py:63` | Medium | Repositories are cloned to `workspace/` but are never deleted, leading to storage leaks over time. | Add a cleanup mechanism or context manager to delete the timestamped directory after analysis is complete or fails. |
| 5 | `backend/graph_store.py:183` | Low | No database uniqueness constraints or indexes are created on `(repo, id)`. | Add initialization logic to create Neo4j constraints: `CREATE CONSTRAINT FOR (n:Entity) REQUIRE (n.repo, n.id) IS UNIQUE`. |
| 6 | `backend/main.py:87` | Low | The `/analyze` endpoint performs cloning and graph extraction synchronously, which will timeout for large repositories. | Implement a background task queue (e.g. Celery or FastAPI BackgroundTasks) and return a job ID. |

## 7. Stage 5 Readiness and Gap Analysis
**Is the graph ready for Impact Analysis?** 
No. Impact analysis inherently asks: *"If I change X, who is affected?"* This requires traversing *upwards/backwards* in the graph (from X to its callers). The current graph model tracks dependencies (what X calls) perfectly via directed edges, but the `find_downstream` logic in `traversal.py` traverses `(start)-[*1..3]->(n)`, which finds what X depends on, not what is impacted by X. 
**Missing Model Elements:**
1. **File-level Dependencies**: We need `IMPORTS` edges between files to determine if changing `utils.py` affects `main.py` directly.
2. **Reverse Traversal Queries**: Cypher queries must traverse backwards: `MATCH (n)<-[*1..3]-(impacted)`.
3. **Test Linking**: To recommend tests, test functions must be linked to the code they exercise (either via CALLS edges to the tested functions or explicit TEST_FOR edges).

## 8. Docs vs Reality Mismatches
* **Tech Stack**: README claims the frontend is React + Tailwind CSS and the database is PostgreSQL (Neon). In reality, the `frontend/` directory is entirely empty, and the backend relies solely on Neo4j for storage. `pipeline.md` claims SQLAlchemy + SQLite is used for MVP, which is false.
* **Features**: README advertises Risk Scoring, AI reasoning (LangChain), and Test Recommendations. None of this code exists in the repository. The `/analyze` endpoint just dumps the graph.
* **Authentication**: Architecture claims JWT authentication, but the FastAPI endpoints are completely unauthenticated.
* **Folder Structure**: README specifies an `app/api/`, `app/core/` layout, but the codebase actually consists of flat Python scripts dumped into `backend/`.

## 9. Recommended Next Steps
1. **Critical Bug Fixes**: Replace the route-matching regex in `analysis.py` with proper AST decorator parsing to eliminate false positive API endpoints.
2. **Database Performance**: Rewrite `graph_store.py` insertion logic to use `UNWIND` batching. Establish Neo4j indexes on `(repo, id)`.
3. **Refactor Call Resolution**: Improve `dependency_graph.py` to utilize import statements when mapping function calls, allowing proper resolution of duplicate function names.
4. **Implement Real Impact Analysis**: Update `traversal.py` to perform reverse path traversal (incoming edges) to find affected upstream components.
5. **Architecture Modernization**: Refactor the flat script structure into the domain-driven architecture (`app/api`, `app/services`) promised by the README, and move synchronous processing into background tasks.

---

## 10. APPENDIX A: Source Code

### `dependency_graph.py` (Excerpt for brevity)
```python
from pathlib import Path
import networkx as nx

class DependencyGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.definitions = {}
    # ...
```

### `graph_store.py` (Excerpt)
```python
from neo4j import GraphDatabase
import config

class Neo4jGraphStore:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
        )
    # ...
```

### `analysis.py` (Excerpt)
```python
import re
from pathlib import Path
from tree_sitter_language_pack import get_parser
# ...
```

### `main.py` (Excerpt)
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# ...
```

### `config.py`
```python
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") # REDACTED
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
```

## 11. APPENDIX B: Sample JSON Output

### Analyzer Output Sample (False positive routes due to `f.get()`)
```json
{
  "path": "analysis.py",
  "language": "python",
  "functions": [
    {
      "name": "analyze",
      "start_line": 173,
      "end_line": 190,
      "calls": ["Path", "root.exists", "ValueError", "self.parse_file", "self.discover_files", "len", "sum", "len", "f.get", "sum", "len", "f.get", "sum", "len", "f.get"]
    }
  ],
  "routes": [
    {
      "method": "GET",
      "path": "functions",
      "line": 186
    },
    {
      "method": "GET",
      "path": "classes",
      "line": 187
    }
  ]
}
```

### Graph Nodes and Edges Sample
**Nodes**:
```json
[
  {"id": "file:analysis.py", "type": "file", "name": "analysis.py"},
  {"id": "file:config.py", "type": "file", "name": "config.py"}
]
```

**Edges**:
```json
[
  {"source": "file:analysis.py", "target": "function:analysis.py:discover_files", "relation": "contains"},
  {"source": "function:analysis.py:parse_file", "target": "function:analysis.py:_read_functions", "relation": "calls"}
]
```
