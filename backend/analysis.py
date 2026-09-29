import re
from pathlib import Path
from tree_sitter_language_pack import get_parser

LANGUAGES = {
    ".py": "python",
}
SKIP_DIRS = {".git", "venv", ".venv", "node_modules", "__pycache__", "dist", "build", "workspace"}

def get_text(node, source: bytes) -> str:
    if not node:
        return ""
    return source[node.start_byte:node.end_byte].decode(errors="ignore")

class PythonVisitor:
    def __init__(self, source: bytes, relative_path: str):
        self.source = source
        self.relative_path = relative_path
        self.functions = []
        self.classes = []
        self.imports = []
        self.routes = []
        
        self.context_stack = [] # to build qualified names
        self.is_test_file = self.check_is_test_file(relative_path)
        
    def check_is_test_file(self, path: str):
        p = Path(path)
        name = p.name
        if name.startswith("test_") or name.endswith("_test.py") or "test" in p.parts:
            return True
        return False
        
    def visit(self, node):
        if not node:
            return
            
        if node.type == "import_statement":
            self.visit_import(node)
        elif node.type == "import_from_statement":
            self.visit_import_from(node)
        elif node.type in ("function_definition", "class_definition"):
            self.visit_def(node, [])
        elif node.type == "decorated_definition":
            decorators = self.get_decorators(node)
            def_node = node.child_by_field_name("definition") or self.find_first(node, {"function_definition", "class_definition"})
            if def_node:
                self.visit_def(def_node, decorators)
            else:
                for child in node.children:
                    self.visit(child)
        else:
            # We also want to find calls that happen at module level, so we just collect them inside visit_def or here?
            # Actually, module level calls belong to the file context. But the prompt says "Functions -CALLS->". 
            # If a call is module level, maybe we just assign it to a dummy module function or attach to file?
            # The prompt says "File -CONTAINS-> Class | module-level Function", "Function -CALLS-> Function".
            # Let's collect calls only inside functions for now, as that's what the prompt asks.
            for child in node.children:
                self.visit(child)

    def find_first(self, node, types):
        if not node: return None
        if node.type in types: return node
        for child in node.children:
            res = self.find_first(child, types)
            if res: return res
        return None

    def get_decorators(self, node):
        decs = []
        for child in node.children:
            if child.type == "decorator":
                decs.append(child)
        return decs
        
    def extract_decorator_info(self, dec_node):
        text = get_text(dec_node, self.source)
        # "@app.get('/path')" -> name="app.get", args="('/path')"
        text = text[1:] # remove @
        if "(" in text:
            idx = text.index("(")
            return text[:idx], text[idx:]
        return text, ""
        
    def parse_route(self, dec_text, line):
        # dec_text like "app.get" or "router.post"
        # look for HTTP methods
        methods = {"get", "post", "put", "delete", "patch", "head", "options", "route"}
        parts = dec_text.lower().split(".")
        method = None
        for p in parts:
            if p in methods:
                method = p
                break
        if method:
            # try to extract path from args? It's better to just regex the args or parse them
            return method.upper()
        return None

    def visit_def(self, node, decorators):
        name_node = node.child_by_field_name("name")
        name = get_text(name_node, self.source) if name_node else "<anonymous>"
        
        qual_name = ".".join(self.context_stack + [name])
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        if decorators and decorators[0].start_point[0] < node.start_point[0]:
            start_line = decorators[0].start_point[0] + 1 # Include decorators
            
        dec_texts = []
        is_route = False
        route_info = None
        
        for dec in decorators:
            dname, dargs = self.extract_decorator_info(dec)
            dec_texts.append(dname + dargs)
            method = self.parse_route(dname, start_line)
            if method:
                # crude path extraction from args: look for first string literal
                path_match = re.search(r"['\"]([^'\"]+)['\"]", dargs)
                path = path_match.group(1) if path_match else "/"
                # check for path= keyword
                path_kw = re.search(r"path\s*=\s*['\"]([^'\"]+)['\"]", dargs)
                if path_kw: path = path_kw.group(1)
                
                is_route = True
                route_info = {"method": method, "path": path}

        is_test = False
        if self.is_test_file and (name.startswith("test_") or name.startswith("Test")):
            is_test = True

        self.context_stack.append(name)
        
        # collect inside
        calls = []
        refs = []
        depends = []
        http_calls = []
        
        self.collect_body(node, calls, refs, depends, http_calls)
        
        if node.type == "class_definition":
            bases = []
            args_node = node.child_by_field_name("superclasses")
            if args_node:
                for child in args_node.children:
                    if child.type not in ("(", ")", ","):
                        bases.append(get_text(child, self.source))
                        
            methods = []
            for child in node.child_by_field_name("body").children if node.child_by_field_name("body") else []:
                if child.type in ("function_definition", "decorated_definition"):
                    mname = self.find_first(child, {"function_definition"}).child_by_field_name("name")
                    if mname: methods.append(get_text(mname, self.source))
                    
            self.classes.append({
                "name": name,
                "qualified_name": qual_name,
                "bases": bases,
                "decorators": dec_texts,
                "methods": methods,
                "start_line": start_line,
                "end_line": end_line,
                "is_test": is_test
            })
            
        elif node.type == "function_definition":
            is_async = False
            if node.prev_sibling and node.prev_sibling.type == "async":
                is_async = True
            
            # Param parsing for depends and types
            params_node = node.child_by_field_name("parameters")
            if params_node:
                for child in params_node.children:
                    if child.type in ("typed_parameter", "typed_default_parameter"):
                        type_node = child.child_by_field_name("type")
                        if type_node:
                            t = get_text(type_node, self.source)
                            refs.append(t)
                    if child.type in ("default_parameter", "typed_default_parameter"):
                        val_node = child.child_by_field_name("value")
                        if val_node and val_node.type == "call":
                            fn = get_text(val_node.child_by_field_name("function"), self.source)
                            if fn == "Depends" or fn == "fastapi.Depends":
                                args = val_node.child_by_field_name("arguments")
                                if args and args.named_child_count > 0:
                                    depends.append(get_text(args.named_children[0], self.source))
            
            ret_node = node.child_by_field_name("return_type")
            if ret_node:
                refs.append(get_text(ret_node, self.source))
                
            owner_class = self.context_stack[-2] if len(self.context_stack) > 1 else None
            
            fn_dict = {
                "name": name,
                "qualified_name": qual_name,
                "owner_class": owner_class,
                "is_async": is_async,
                "decorators": dec_texts,
                "start_line": start_line,
                "end_line": end_line,
                "calls": calls,
                "references": refs,
                "depends": depends,
                "http_calls": http_calls,
                "is_test": is_test
            }
            self.functions.append(fn_dict)
            
            if is_route and route_info:
                self.routes.append({
                    "method": route_info["method"],
                    "path": route_info["path"],
                    "handler": qual_name,
                    "line": start_line
                })
        
        # Traverse children to find nested defs
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                self.visit(child)
                
        self.context_stack.pop()
        
    def collect_body(self, node, calls, refs, depends, http_calls):
        # find calls and refs in body without entering nested defs
        def walk(n):
            if not n: return
            if n.type in ("function_definition", "class_definition", "decorated_definition"):
                return
            if n.type == "call":
                fn_node = n.child_by_field_name("function")
                fn_text = get_text(fn_node, self.source)
                
                # Check HTTP calls
                args_node = n.child_by_field_name("arguments")
                is_http = False
                if fn_text.startswith("client.") or fn_text.startswith("requests.") or fn_text.startswith("self.client.") or fn_text.startswith("httpx."):
                    parts = fn_text.split(".")
                    method = parts[-1].upper()
                    if method in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                        if args_node and args_node.named_child_count > 0:
                            path_arg = args_node.named_children[0]
                            if path_arg.type == "string":
                                path_val = get_text(path_arg, self.source).strip("'\"")
                                http_calls.append({"method": method, "path": path_val, "line": n.start_point[0]+1})
                                is_http = True
                                
                if not is_http:
                    # Clean up fn_text: remove newlines, limit to statically knowable
                    # If it's a complex expression like foo()[1].bar, just mark dynamic
                    dynamic = False
                    if "\n" in fn_text or "[" in fn_text or "(" in fn_text:
                        dynamic = True
                        if "." in fn_text:
                            # crude static part
                            fn_text = fn_text.split(".")[-1]
                        else:
                            fn_text = "dynamic"
                            
                    if len(fn_text) > 100: fn_text = fn_text[:100]
                    calls.append({"name": fn_text, "dynamic": dynamic, "line": n.start_point[0]+1})
                    
            elif n.type == "type":
                refs.append(get_text(n, self.source))
                
            for child in n.children:
                walk(child)
        
        body = node.child_by_field_name("body")
        if body: walk(body)

    def visit_import(self, node):
        # import a.b, c.d as e
        for child in node.children:
            if child.type == "dotted_name":
                self.imports.append({"module": None, "name": get_text(child, self.source), "alias": None, "level": 0, "line": node.start_point[0]+1})
            elif child.type == "aliased_import":
                name = get_text(child.child_by_field_name("name"), self.source)
                alias = get_text(child.child_by_field_name("alias"), self.source)
                self.imports.append({"module": None, "name": name, "alias": alias, "level": 0, "line": node.start_point[0]+1})

    def visit_import_from(self, node):
        module_node = node.child_by_field_name("module_name")
        module_name = get_text(module_node, self.source) if module_node else ""
        
        # count dots for relative level
        level = 0
        for child in node.children:
            if child.type == "relative_import":
                level = get_text(child, self.source).count(".")
            elif child.type == "." and not module_name:
                level += 1
                
        # items
        for child in node.children:
            if child.type == "dotted_name":
                self.imports.append({"module": module_name, "name": get_text(child, self.source), "alias": None, "level": level, "line": node.start_point[0]+1})
            elif child.type == "aliased_import":
                name = get_text(child.child_by_field_name("name"), self.source)
                alias = get_text(child.child_by_field_name("alias"), self.source)
                self.imports.append({"module": module_name, "name": name, "alias": alias, "level": level, "line": node.start_point[0]+1})
            elif child.type == "wildcard_import":
                self.imports.append({"module": module_name, "name": "*", "alias": None, "level": level, "line": node.start_point[0]+1})


class RepositoryAnalyzer:
    def discover_files(self, repo_path: Path) -> list[Path]:
        files = []
        for path in repo_path.rglob("*"):
            if path.suffix not in LANGUAGES:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
        return files

    def parse_file(self, file_path: Path, repo_path: Path) -> dict:
        language = LANGUAGES.get(file_path.suffix, "python")
        relative = file_path.relative_to(repo_path).as_posix()
        
        try:
            source = file_path.read_bytes()
            tree = get_parser(language).parse(source)
            root = tree.root_node
            
            visitor = PythonVisitor(source, relative)
            visitor.visit(root)
            
            return {
                "path": relative,
                "language": language,
                "functions": visitor.functions,
                "classes": visitor.classes,
                "imports": visitor.imports,
                "routes": visitor.routes,
                "is_test": visitor.is_test_file
            }
        except Exception as e:
            return {"path": relative, "language": language, "error": str(e)}

    def analyze(self, repo_path: str) -> dict:
        root = Path(repo_path)
        if not root.exists():
            raise ValueError("Repository path does not exist.")

        files = []
        parse_errors = 0
        for f in self.discover_files(root):
            res = self.parse_file(f, root)
            if "error" in res:
                parse_errors += 1
            files.append(res)

        return {
            "files": files,
            "summary": {
                "file_count": len(files),
                "function_count": sum(len(f.get("functions", [])) for f in files),
                "class_count": sum(len(f.get("classes", [])) for f in files),
                "route_count": sum(len(f.get("routes", [])) for f in files),
                "parse_errors": parse_errors
            },
        }
