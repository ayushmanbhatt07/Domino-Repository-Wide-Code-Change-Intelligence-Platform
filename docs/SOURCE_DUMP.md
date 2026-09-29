## backend/analysis.py
```python
import re
from pathlib import Path

from tree_sitter_language_pack import get_parser


# File extension -> tree-sitter language name.
LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
}

# Folders we never want to look inside.
SKIP_DIRS = {".git", "venv", ".venv", "node_modules", "__pycache__", "dist", "build"}

# The same idea has a different node name in each language's grammar,
# so we group the names we care about.
FUNCTION_NODES = {"function_definition", "function_declaration",
                  "method_declaration", "method_definition"}
CLASS_NODES = {"class_definition", "class_declaration"}
IMPORT_NODES = {"import_statement", "import_from_statement", "import_declaration"}
CALL_NODES = {"call", "call_expression", "method_invocation"}

# Finds "@app.get('/x')" or "router.post('/y')" style route definitions.
ROUTE_PATTERN = re.compile(r"\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]")


class RepositoryAnalyzer:
    """
    Reads a cloned repository without running it and extracts:
    functions, classes, imports and API routes from every source file.
    """

    # -----------------------------
    # Find the source files
    # -----------------------------
    def discover_files(self, repo_path: Path) -> list[Path]:

        files = []

        for path in repo_path.rglob("*"):

            if path.suffix not in LANGUAGES:
                continue

            if any(part in SKIP_DIRS for part in path.parts):
                continue

            files.append(path)

        return files

    # -----------------------------
    # Small helpers
    # -----------------------------
    def _text(self, node, source: bytes) -> str:
        return source[node.start_byte:node.end_byte].decode(errors="ignore")

    def _name(self, node, source: bytes):
        name_node = node.child_by_field_name("name")
        return self._text(name_node, source) if name_node else None

    def _find(self, node, wanted: set):
        """Every descendant of node whose type is in `wanted`."""
        found = []

        for child in node.children:
            if child.type in wanted:
                found.append(child)
            found.extend(self._find(child, wanted))

        return found

    # -----------------------------
    # Read one file
    # -----------------------------
    def parse_file(self, file_path: Path, repo_path: Path) -> dict:

        language = LANGUAGES[file_path.suffix]
        relative = str(file_path.relative_to(repo_path))

        try:
            source = file_path.read_bytes()
            tree = get_parser(language).parse(source)
            root = tree.root_node

            functions = self._read_functions(root, source)
            classes = self._read_classes(root, source)
            imports = self._read_imports(root, source)
            routes = self._read_routes(root, source)

            return {
                "path": relative,
                "language": language,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "routes": routes,
            }

        except Exception as e:
            return {"path": relative, "language": language, "error": str(e)}

    def _read_functions(self, root, source: bytes) -> list:

        functions = []

        for node in self._find(root, FUNCTION_NODES):

            calls = [self._callee(call, source) for call in self._find(node, CALL_NODES)]

            functions.append({
                "name": self._name(node, source),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "calls": [c for c in calls if c],
            })

        return functions

    def _read_classes(self, root, source: bytes) -> list:

        classes = []

        for node in self._find(root, CLASS_NODES):

            methods = [self._name(m, source) for m in self._find(node, FUNCTION_NODES)]

            classes.append({
                "name": self._name(node, source),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "methods": [m for m in methods if m],
            })

        return classes

    def _read_imports(self, root, source: bytes) -> list:

        return [self._text(node, source) for node in self._find(root, IMPORT_NODES)]

    def _read_routes(self, root, source: bytes) -> list:

        routes = []

        for call in self._find(root, CALL_NODES):

            match = ROUTE_PATTERN.search(self._text(call, source))

            if match:
                routes.append({
                    "method": match.group(1).upper(),
                    "path": match.group(2),
                    "line": call.start_point[0] + 1,
                })

        return routes

    def _callee(self, call, source: bytes):
        """The name being called, e.g. 'bar' or 'app.get'."""
        target = call.child_by_field_name("function") or call.child_by_field_name("name")
        return self._text(target, source) if target else None

    # -----------------------------
    # Main entry point
    # -----------------------------
    def analyze(self, repo_path: str) -> dict:

        root = Path(repo_path)

        if not root.exists():
            raise ValueError("Repository path does not exist.")

        files = [self.parse_file(f, root) for f in self.discover_files(root)]

        return {
            "files": files,
            "summary": {
                "file_count": len(files),
                "function_count": sum(len(f.get("functions", [])) for f in files),
                "class_count": sum(len(f.get("classes", [])) for f in files),
                "route_count": sum(len(f.get("routes", [])) for f in files),
            },
        }

```

## backend/dependency_graph.py
```python
from pathlib import Path
import networkx as nx


class DependencyGraphBuilder:
    """
    Builds a repository dependency graph from the output
    produced by RepositoryAnalyzer.

    Graph type: Directed Graph (DiGraph), because relationships
    have a direction:

        file      --contains--> function
        route     --handled_by--> function
        function  --calls--> function   (resolved to the real definition)
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.definitions = {}

    # -------------------------------------------------
    # File nodes
    # -------------------------------------------------
    def _add_files(self, analysis):

        for file in analysis["files"]:

            self.graph.add_node(
                f"file:{file['path']}",
                type="file",
                name=file["path"]
            )

    # -------------------------------------------------
    # Function nodes  (file --contains--> function)
    # -------------------------------------------------
    def _add_functions(self, analysis):

        for file in analysis["files"]:

            file_node = f"file:{file['path']}"

            for function in file.get("functions", []):

                function_node = f"function:{file['path']}:{function['name']}"

                self.graph.add_node(
                    function_node,
                    type="function",
                    name=function["name"],
                    start_line=function["start_line"],
                    end_line=function["end_line"]
                )

                self.graph.add_edge(file_node, function_node, relation="contains")

    # -------------------------------------------------
    # Class nodes  (file --contains--> class)
    # -------------------------------------------------
    def _add_classes(self, analysis):

        for file in analysis["files"]:

            file_node = f"file:{file['path']}"

            for cls in file.get("classes", []):

                class_node = f"class:{file['path']}:{cls['name']}"

                self.graph.add_node(class_node, type="class", name=cls["name"])

                self.graph.add_edge(file_node, class_node, relation="contains")

    # -------------------------------------------------
    # Index every definition by its name.
    # Used to resolve calls to the real function/class.
    # -------------------------------------------------
    def _index_definitions(self, analysis):

        for file in analysis["files"]:

            path = file["path"]

            for function in file.get("functions", []):
                node = f"function:{path}:{function['name']}"
                self.definitions.setdefault(function["name"], []).append(node)

            for cls in file.get("classes", []):
                node = f"class:{path}:{cls['name']}"
                self.definitions.setdefault(cls["name"], []).append(node)

    # -------------------------------------------------
    # Route nodes  (route --handled_by--> function)
    # -------------------------------------------------
    def _add_routes(self, analysis):

        for file in analysis["files"]:

            functions = file.get("functions", [])

            for route in file.get("routes", []):

                route_node = f"route:{route['method']}:{route['path']}"

                self.graph.add_node(
                    route_node,
                    type="route",
                    method=route["method"],
                    path=route["path"]
                )

                # A route decorator sits directly above its handler,
                # so the handler is the first function after the route's line.
                handler = self._function_after(route.get("line"), functions)

                if handler:
                    function_node = f"function:{file['path']}:{handler}"
                    self.graph.add_edge(route_node, function_node, relation="handled_by")

    def _function_after(self, line, functions):

        if line is None:
            return None

        below = [f for f in functions if f["start_line"] >= line]

        if not below:
            return None

        return min(below, key=lambda f: f["start_line"])["name"]

    # -------------------------------------------------
    # Call edges  (function --calls--> function)
    # -------------------------------------------------
    def _add_calls(self, analysis):

        for file in analysis["files"]:

            path = file["path"]

            for function in file.get("functions", []):

                source = f"function:{path}:{function['name']}"

                for call in function.get("calls", []):

                    target = self._resolve(call)

                    if target:
                        # Call to our own code -> link to the real definition.
                        self.graph.add_edge(source, target, relation="calls")
                    else:
                        # Library / built-in call we can't resolve.
                        external_node = f"external:{call}"
                        self.graph.add_node(external_node, type="external", name=call)
                        self.graph.add_edge(source, external_node, relation="calls")

    def _resolve(self, call):
        """
        Turn a call name into the node it refers to, if it is our own code.

        - "add_one"          -> look up add_one
        - "self.assertEqual" -> look up assertEqual (a method on this object)
        - "os.listdir"       -> external, don't resolve (module.function)

        Returns the node id only when exactly one definition matches,
        otherwise None (treated as external).
        """
        if "." not in call:
            candidate = call
        elif call.startswith("self."):
            candidate = call.split(".", 1)[1]
        else:
            return None

        matches = self.definitions.get(candidate, [])

        return matches[0] if len(matches) == 1 else None

    # -------------------------------------------------
    # Build
    # -------------------------------------------------
    def build(self, analysis):

        self._add_files(analysis)
        self._add_functions(analysis)
        self._add_classes(analysis)

        # Index definitions before resolving routes and calls.
        self._index_definitions(analysis)

        self._add_routes(analysis)
        self._add_calls(analysis)

        return self.graph

    # -------------------------------------------------
    # Summary
    # -------------------------------------------------
    def summary(self):

        external = self._external_call_count()
        total_calls = sum(
            1 for _, _, data in self.graph.edges(data=True)
            if data["relation"] == "calls"
        )

        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "internal_calls": total_calls - external,
            "external_calls": external,
        }

    def _external_call_count(self):
        return sum(
            1 for _, target in self.graph.edges()
            if self.graph.nodes[target]["type"] == "external"
        )

    # -------------------------------------------------
    # Export  (each repo saved to its own file)
    # -------------------------------------------------
    def export_graphml(self, output_path: str):

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        nx.write_graphml(self.graph, path)

```

## backend/graph_store.py
```python
from neo4j import GraphDatabase

import config


# Our graph "type" -> a proper Neo4j label (nicer to query and view).
LABELS = {
    "file": "File",
    "function": "Function",
    "class": "Class",
    "route": "Route",
    "external": "External",
}

# Our edge "relation" -> a proper Neo4j relationship type.
RELATIONS = {
    "contains": "CONTAINS",
    "calls": "CALLS",
    "handled_by": "HANDLED_BY",
}


class Neo4jGraphStore:
    """
    Saves a dependency graph (a networkx DiGraph) into Neo4j.

    Every node and relationship is tagged with `repo`, so re-analyzing
    a repository replaces only that repository's data.
    """

    def __init__(self):
        self.driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    # -------------------------------------------------
    # Save one repository's graph
    # -------------------------------------------------
    def save(self, repo: str, graph):

        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            session.execute_write(self._replace_repo, repo, graph)

    @staticmethod
    def _replace_repo(tx, repo, graph):

        # 1. Remove this repo's old graph so we never duplicate.
        tx.run("MATCH (n {repo: $repo}) DETACH DELETE n", repo=repo)

        # 2. Write every node.
        for node_id, data in graph.nodes(data=True):

            label = LABELS.get(data.get("type"), "Entity")
            props = dict(data)
            props["id"] = node_id
            props["repo"] = repo

            tx.run(
                f"MERGE (n:{label} {{id: $id, repo: $repo}}) SET n += $props",
                id=node_id, repo=repo, props=props
            )

        # 3. Write every relationship.
        for source, target, data in graph.edges(data=True):

            rel = RELATIONS.get(data["relation"], "RELATED")

            tx.run(
                f"""
                MATCH (a {{id: $source, repo: $repo}})
                MATCH (b {{id: $target, repo: $repo}})
                MERGE (a)-[:{rel}]->(b)
                """,
                source=source, target=target, repo=repo
            )

# -------------------------------------------------
# Find a function
# -------------------------------------------------
def find_function(self, repo: str, function_name: str):

    query = """
    MATCH (f:Function {repo: $repo, name: $name})
    RETURN f
    """

    with self.driver.session(database=config.NEO4J_DATABASE) as session:

        result = session.run(
            query,
            repo=repo,
            name=function_name
        )

        record = result.single()

        if record is None:
            return None

        return dict(record["f"])

# -------------------------------------------------
# Find a file
# -------------------------------------------------
def find_file(self, repo: str, file_name: str):

    query = """
    MATCH (f:File {repo: $repo, name: $name})
    RETURN f
    """

    with self.driver.session(database=config.NEO4J_DATABASE) as session:

        result = session.run(
            query,
            repo=repo,
            name=file_name
        )

        record = result.single()

        if record is None:
            return None

        return dict(record["f"])

# -------------------------------------------------
# Find a class
# -------------------------------------------------
def find_class(self, repo: str, class_name: str):

    query = """
    MATCH (c:Class {repo: $repo, name: $name})
    RETURN c
    """

    with self.driver.session(database=config.NEO4J_DATABASE) as session:

        result = session.run(
            query,
            repo=repo,
            name=class_name
        )

        record = result.single()

        if record is None:
            return None

        return dict(record["c"])


# -------------------------------------------------
# Find a route
# -------------------------------------------------
def find_route(self, repo: str, route: str):

    query = """
    MATCH (r:Route {repo: $repo, path: $path})
    RETURN r
    """

    with self.driver.session(database=config.NEO4J_DATABASE) as session:

        result = session.run(
            query,
            repo=repo,
            path=route
        )

        record = result.single()

        if record is None:
            return None

        return dict(record["r"])


def find_entity(
    self,
    repo: str,
    entity_type: str,
    name: str
):
    """
    Find a single entity in a repository graph.

    entity_type:
        file
        function
        class
        route
    """

    label = {
        "file": "File",
        "function": "Function",
        "class": "Class",
        "route": "Route",
    }.get(entity_type)

    if label is None:
        raise ValueError(f"Unsupported entity type: {entity_type}")

    property_name = "path" if entity_type == "route" else "name"

    query = f"""
    MATCH (n:{label} {{repo: $repo, {property_name}: $name}})
    RETURN n
    LIMIT 1
    """

    with self.driver.session(
        database=config.NEO4J_DATABASE
    ) as session:

        result = session.run(
            query,
            repo=repo,
            name=name
        )

        record = result.single()

        if record is None:
            return None

        node = record["n"]

        return {
            "id": node.get("id"),
            "type": node.get("type"),
            "name": node.get("name"),
            "path": node.get("path"),
            "method": node.get("method"),
            "repo": node.get("repo"),
        }
def find_downstream(
    self,
    repo: str,
    node_id: str,
    depth: int = 3,
):
    query = f"""
    MATCH (start {{repo: $repo, id: $node_id}})
    MATCH (start)-[*1..{depth}]->(n)
    WHERE n.repo = $repo
    RETURN DISTINCT n
    """

    with self.driver.session(
        database=config.NEO4J_DATABASE
    ) as session:

        result = session.run(
            query,
            repo=repo,
            node_id=node_id
        )

        nodes = []

        for record in result:
            node = record["n"]

            nodes.append({
                "id": node.get("id"),
                "type": node.get("type"),
                "name": node.get("name"),
                "path": node.get("path"),
                "method": node.get("method"),
                "repo": node.get("repo"),
            })

        return nodes
```

## backend/ingestion.py
```python
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

import requests
from git import Repo, GitCommandError


class RepositoryIngestionService:
    """
    Handles:
    1. URL Validation
    2. Repository Existence Check
    3. Repository Cloning
    """ 

    def __init__(self):
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)

    # -----------------------------
    # Validate URL
    # -----------------------------
    def validate_url(self, repo_url: str) -> bool:

        parsed = urlparse(repo_url)

        if parsed.scheme not in ("http", "https"):
            return False

        if parsed.netloc != "github.com":
            return False

        path = parsed.path.strip("/").split("/")

        if len(path) < 2:
            return False

        return True

    # -----------------------------
    # Check Repository Exists
    # -----------------------------
    def repository_exists(self, repo_url: str) -> bool:

        response = requests.get(repo_url)

        return response.status_code == 200

    # -----------------------------
    # Clone Repository
    # -----------------------------
    def clone_repository(self, repo_url: str):

        repo_name = repo_url.rstrip("/").split("/")[-1]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        folder_name = f"{repo_name}_{timestamp}"

        clone_path = self.workspace / folder_name

        Repo.clone_from(repo_url, clone_path)

        return {
            "repository": repo_name,
            "path": str(clone_path)
        }

    # -----------------------------
    # Main Pipeline
    # -----------------------------
    def ingest(self, repo_url: str):

        if not self.validate_url(repo_url):
            raise ValueError("Invalid GitHub Repository URL.")

        if not self.repository_exists(repo_url):
            raise ValueError("Repository does not exist or is inaccessible.")

        try:

            result = self.clone_repository(repo_url)

            return result

        except GitCommandError as e:

            raise RuntimeError(f"Git Clone Failed : {e}")
```

## backend/main.py
```python
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ingestion import RepositoryIngestionService
from analysis import RepositoryAnalyzer
from dependency_graph import DependencyGraphBuilder
from graph_store import Neo4jGraphStore

app = FastAPI(
    title="Domino",
    version="0.1",
    description="Repository-Wide Code Change Intelligence Platform"
)


service = RepositoryIngestionService()
analyzer = RepositoryAnalyzer()
store = Neo4jGraphStore()

# -----------------------------
# Request Model
# -----------------------------
class RepositoryRequest(BaseModel):
    repo_url: str


class AnalyzeRequest(BaseModel):
    path: str


# -----------------------------
# Home
# -----------------------------
@app.get("/")
def home():

    return {
        "message": "Domino Backend Running"
    }


# -----------------------------
# Repository Ingestion
# -----------------------------
@app.post("/ingest")
def ingest_repository(request: RepositoryRequest):

    try:

        result = service.ingest(request.repo_url)

        return {
            "status": "success",
            "repository": result["repository"],
            "local_path": result["path"],
            "message": "Repository cloned successfully."
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except RuntimeError as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -----------------------------
# Repository Analysis
# -----------------------------
@app.post("/analyze")
def analyze_repository(request: AnalyzeRequest):

    try:

        # -----------------------------
        # Stage 2 - Repository Analysis
        # -----------------------------
        result = analyzer.analyze(request.path)

        # -----------------------------
        # Stage 3 - Dependency Graph
        # Create a fresh graph builder for every request
        # -----------------------------
        graph_builder = DependencyGraphBuilder()

        graph = graph_builder.build(result)

        # -----------------------------
        # Print Graph Summary
        # -----------------------------
        print("\n========== GRAPH SUMMARY ==========")
        print(graph_builder.summary())

        # -----------------------------
        # Print All Nodes
        # -----------------------------
        print("\n========== NODES ==========")

        for node, data in graph.nodes(data=True):
            print(node, data)

        # -----------------------------
        # Print All Edges
        # -----------------------------
        print("\n========== EDGES ==========")

        for source, target, data in graph.edges(data=True):
            print(f"{source} --{data['relation']}--> {target}")

        # -----------------------------
        # Export Graph (one file per repo, so nothing is overwritten)
        # -----------------------------
        repo_name = Path(request.path).name
        graph_file = f"graphs/{repo_name}.graphml"
        graph_builder.export_graphml(graph_file)

        # -----------------------------
        # Stage 4 - Persist to Neo4j
        # A DB error should not throw away the analysis result.
        # -----------------------------
        try:
            store.save(repo_name, graph)
            stored_in_neo4j = True
        except Exception as e:
            print("Neo4j store failed:", e)
            stored_in_neo4j = False

        # -----------------------------
        # API Response
        # -----------------------------
        return {
            "status": "success",
            "graph_summary": graph_builder.summary(),
            "graph_file": graph_file,
            "stored_in_neo4j": stored_in_neo4j,
            **result
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
```

## backend/config.py
```python
import os

from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "[REDACTED]")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

```

## backend/impact_analysis/matcher.py
```python
class ImpactMatcher:

    def __init__(self, graph_store):
        self.graph_store = graph_store

    def match(
        self,
        repo: str,
        file_name=None,
        function_name=None,
        class_name=None,
        route=None,
    ):
        supplied = [
            ("file", file_name),
            ("function", function_name),
            ("class", class_name),
            ("route", route),
        ]

        supplied = [
            (entity_type, value)
            for entity_type, value in supplied
            if value is not None
        ]

        if len(supplied) == 0:
            raise ValueError(
                "At least one of file_name, function_name, "
                "class_name, or route must be provided."
            )

        if len(supplied) > 1:
            raise ValueError(
                "Provide only one changed entity at a time."
            )

        entity_type, value = supplied[0]

        entity = self.graph_store.find_entity(
            repo=repo,
            entity_type=entity_type,
            name=value
        )

        if entity is None:
            raise ValueError(
                f"{entity_type} '{value}' was not found "
                f"in repository '{repo}'."
            )

        return entity
```

## backend/impact_analysis/models.py
```python
from typing import Optional

from pydantic import BaseModel, Field


class ImpactAnalysisRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier stored in Neo4j")

    file_name: Optional[str] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    route: Optional[str] = None

    depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum graph traversal depth"
    )

class ImpactedNode(BaseModel):
    id: str
    type: str
    name: Optional[str] = None


class ImpactAnalysisResponse(BaseModel):
    status: str
    changed_entity: ImpactedNode
    impacted_nodes: list[ImpactedNode]
```

## backend/impact_analysis/traversal.py
```python
class ImpactTraversal:

    def __init__(self, graph_store):
        self.graph_store = graph_store

    def downstream(
        self,
        repo: str,
        node_id: str,
        depth: int = 3,
    ):
        return self.graph_store.find_downstream(
            repo=repo,
            node_id=node_id,
            depth=depth
        )
```

## backend/test_impact.py
```python
from graph_store import Neo4jGraphStore

from impact_analysis.service import ImpactAnalysisService


store = Neo4jGraphStore()

service = ImpactAnalysisService(store)

result = service.analyze(
    repo="YOUR_REPO_NAME",
    function_name="delete_book",
    depth=3,
)

print("\n========== IMPACT ANALYSIS ==========")

print("Changed entity:")
print(result["changed_entity"])

print("\nImpacted nodes:")

for node in result["impacted_nodes"]:
    print(node)

store.close()
```

## backend/requirements.txt
```python
fastapi
uvicorn[standard]

pydantic
python-dotenv

gitpython

tree-sitter
tree-sitter-language-pack

neo4j

networkx

sqlalchemy

python-multipart

requests

rich

loguru
```
