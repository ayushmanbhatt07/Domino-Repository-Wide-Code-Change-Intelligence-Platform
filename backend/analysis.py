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
