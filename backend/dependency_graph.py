import networkx as nx
from pathlib import Path
import re

class DependencyGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        # Indexes for fast resolution
        self.repo = ""
        self.files = {} # path -> file dict
        self.classes = {} # path -> [class dicts]
        self.functions = {} # path -> [func dicts]
        self.routes = []
        
        # Name indexes
        self.func_by_qualname = {} # qualname -> [nodes]
        self.func_by_name = {} # name -> [nodes]
        self.class_by_qualname = {} # qualname -> [nodes]
        self.class_by_name = {} # name -> [nodes]
        self.node_to_file = {}

    def _normalize_path(self, p):
        return Path(p).as_posix()

    def build(self, analysis):
        self.repo = analysis.get("summary", {}).get("repository", "")
        self.graph = nx.DiGraph(
            repo=self.repo,
            commit_sha=analysis.get("commit_sha", "unknown"),
            analyzed_at=analysis.get("analyzed_at", "unknown"),
            parse_errors=analysis.get("summary", {}).get("parse_errors", 0)
        )
        
        # Index all files, classes, functions
        for f in analysis["files"]:
            if "error" in f: continue
            path = self._normalize_path(f["path"])
            self.files[path] = f
            self.classes[path] = f.get("classes", [])
            self.functions[path] = f.get("functions", [])
            self.routes.extend(f.get("routes", []))
            
            # File Node
            file_node = f"file:{path}"
            self.graph.add_node(file_node, type="file", name=path, path=path, is_test=f.get("is_test", False))
            
            # Class Nodes
            for cls in self.classes[path]:
                cls_node = f"class:{path}:{cls['qualified_name']}"
                self.graph.add_node(cls_node, type="class", name=cls["name"], qualified_name=cls["qualified_name"],
                                    path=path, start_line=cls["start_line"], end_line=cls["end_line"], is_test=cls.get("is_test", False))
                self.graph.add_edge(file_node, cls_node, relation="contains", resolution="exact", confidence=1.0)
                
                self.class_by_qualname.setdefault(cls["qualified_name"], []).append(cls_node)
                self.class_by_name.setdefault(cls["name"], []).append(cls_node)
                self.node_to_file[cls_node] = path
                
            # Function Nodes
            for fn in self.functions[path]:
                fn_node = f"function:{path}:{fn['qualified_name']}"
                self.graph.add_node(fn_node, type="function", name=fn["name"], qualified_name=fn["qualified_name"],
                                    path=path, start_line=fn["start_line"], end_line=fn["end_line"], is_test=fn.get("is_test", False),
                                    is_async=fn.get("is_async", False), unresolved_calls=0)
                
                # If owner_class is set, link from class, else from file
                owner = fn.get("owner_class")
                if owner:
                    # Find class node
                    cls_qual = fn["qualified_name"].rsplit(".", 1)[0]
                    cls_node = f"class:{path}:{cls_qual}"
                    self.graph.add_edge(cls_node, fn_node, relation="contains", resolution="exact", confidence=1.0)
                else:
                    self.graph.add_edge(file_node, fn_node, relation="contains", resolution="exact", confidence=1.0)
                    
                self.func_by_qualname.setdefault(fn["qualified_name"], []).append(fn_node)
                self.func_by_name.setdefault(fn["name"], []).append(fn_node)
                self.node_to_file[fn_node] = path

        # Route Nodes
        route_counts = {}
        for r in self.routes:
            handler = r["handler"]
            method = r["method"]
            path_str = r["path"]
            base_node = f"route:{method}:{path_str}"
            if base_node in route_counts:
                route_counts[base_node] += 1
                route_node = f"{base_node}@{route_counts[base_node]}"
            else:
                route_counts[base_node] = 1
                route_node = base_node
                
            self.graph.add_node(route_node, type="route", name=path_str, method=method, path=path_str, start_line=r["line"])
            
            # Find handler function
            # the handler is just the qualname from the same file. But we don't have the file info directly in routes?
            # Wait, routes were extracted inside parse_file, we attached them there.
            # In analysis.py I put routes inside files. Let's find which file it belongs to.
        for path, f in self.files.items():
            for r in f.get("routes", []):
                handler = r["handler"]
                method = r["method"]
                path_str = r["path"]
                # Recalculate route node (could be collision)
                # Actually I can just re-iterate file by file
                base_node = f"route:{method}:{path_str}"
                
        # Better: reset route_counts
        route_counts = {}
        for path, f in self.files.items():
            for r in f.get("routes", []):
                handler = r["handler"]
                method = r["method"]
                path_str = r["path"]
                base_node = f"route:{method}:{path_str}"
                route_counts[base_node] = route_counts.get(base_node, 0) + 1
                route_node = base_node if route_counts[base_node] == 1 else f"{base_node}@{route_counts[base_node]}"
                
                # handled_by
                fn_node = f"function:{path}:{handler}"
                if fn_node in self.graph:
                    self.graph.add_edge(route_node, fn_node, relation="handled_by", resolution="exact", confidence=1.0)

        # File Imports
        self._resolve_imports()
        
        # Inheritance
        self._resolve_inheritance()
        
        # Calls, Refs, Depends, HTTP
        self._resolve_function_dependencies()
        
        return self.graph

    def _resolve_imports(self):
        # Build module to path map
        # e.g. "app.utils" -> "app/utils.py" or "app/utils/__init__.py"
        module_to_path = {}
        for p in self.files.keys():
            mod = p.replace(".py", "").replace("/", ".")
            if mod.endswith(".__init__"):
                mod = mod[:-9]
            module_to_path[mod] = p

        for path, f in self.files.items():
            file_node = f"file:{path}"
            for imp in f.get("imports", []):
                mod = imp["module"]
                level = imp["level"]
                
                # Resolving module path
                target_mod = ""
                if level > 0:
                    parts = path.split("/")
                    # remove filename and go up 'level' times
                    base_parts = parts[:-level]
                    if mod:
                        target_mod = ".".join(base_parts + [mod])
                    else:
                        target_mod = ".".join(base_parts)
                else:
                    target_mod = mod
                    
                target_path = module_to_path.get(target_mod)
                # If not found, maybe importing a specific symbol from a module that matches a file
                if not target_path and target_mod:
                    # try to see if it's app.models.User (where app.models is the file)
                    parts = target_mod.split(".")
                    for i in range(len(parts), 0, -1):
                        prefix = ".".join(parts[:i])
                        if prefix in module_to_path:
                            target_path = module_to_path[prefix]
                            break

                if target_path:
                    self.graph.add_edge(file_node, f"file:{target_path}", relation="imports", resolution="exact", confidence=1.0)

    def _resolve_inheritance(self):
        for path, cls_list in self.classes.items():
            for cls in cls_list:
                cls_node = f"class:{path}:{cls['qualified_name']}"
                for base in cls.get("bases", []):
                    # resolve base
                    res = self._resolve_name(base, path)
                    if res:
                        for n, res_type, conf in res:
                            if "class:" in n:
                                self.graph.add_edge(cls_node, n, relation="inherits", resolution=res_type, confidence=conf)

    def _resolve_function_dependencies(self):
        for path, fn_list in self.functions.items():
            for fn in fn_list:
                fn_node = f"function:{path}:{fn['qualified_name']}"
                
                # Calls
                for call in fn.get("calls", []):
                    if call.get("dynamic"):
                        self.graph.nodes[fn_node]["unresolved_calls"] += 1
                        continue
                        
                    targets = self._resolve_call(call["name"], path, fn.get("owner_class"), fn["qualified_name"])
                    if not targets:
                        self.graph.nodes[fn_node]["unresolved_calls"] += 1
                    else:
                        for target, res_type, conf in targets:
                            if target.startswith("external:"):
                                if target not in self.graph:
                                    self.graph.add_node(target, type="external", name=target.split(":",1)[1])
                                self.graph.add_edge(fn_node, target, relation="calls", resolution=res_type, confidence=conf, line=call.get("line"))
                            else:
                                self.graph.add_edge(fn_node, target, relation="calls", resolution=res_type, confidence=conf, line=call.get("line"))
                                
                # Depends
                for dep in fn.get("depends", []):
                    targets = self._resolve_name(dep, path)
                    if targets:
                        for t, res_type, conf in targets:
                            self.graph.add_edge(fn_node, t, relation="calls", resolution="depends", confidence=1.0)
                            
                # References
                for ref in fn.get("references", []):
                    targets = self._resolve_name(ref, path)
                    if targets:
                        for t, res_type, conf in targets:
                            if "class:" in t:
                                self.graph.add_edge(fn_node, t, relation="references", resolution=res_type, confidence=conf)
                                
                # HTTP EXERCISES
                for http in fn.get("http_calls", []):
                    # Match route templates against literal paths
                    matched_route = self._match_route(http["method"], http["path"])
                    if matched_route:
                        self.graph.add_edge(fn_node, matched_route, relation="exercises", resolution="http_call", confidence=0.7, line=http.get("line"))

    def _match_route(self, method, path):
        # find matching route in graph
        for n, data in self.graph.nodes(data=True):
            if data.get("type") == "route":
                if data["method"] == method:
                    # simplistic match: replace {xxx} with regex [^/]+
                    route_path = data["path"]
                    pattern = re.sub(r'\{[^}]+\}', '[^/]+', route_path)
                    pattern = f"^{pattern}$"
                    if re.match(pattern, path):
                        return n
        return None

    def _resolve_call(self, name, current_path, owner_class, fn_qual):
        # 1. self.x / cls.x -> method in same class / base class
        if name.startswith("self.") or name.startswith("cls."):
            method_name = name.split(".", 1)[1]
            if owner_class:
                # Find method in current class
                curr_cls_node = f"class:{current_path}:{owner_class}"
                # We can check same class
                meth_node = f"function:{current_path}:{owner_class}.{method_name}"
                if meth_node in self.graph:
                    return [(meth_node, "self", 1.0)]
                # Check bases (rudimentary)
                return self._search_bases(curr_cls_node, method_name, "self")
            return []
            
        # 2. super().x -> nearest base class method
        if name.startswith("super()."):
            method_name = name.split(".", 1)[1]
            if owner_class:
                curr_cls_node = f"class:{current_path}:{owner_class}"
                return self._search_bases(curr_cls_node, method_name, "super")
            return []
            
        # fallback to general name resolution
        return self._resolve_name(name, current_path)

    def _search_bases(self, cls_node, method_name, res_type):
        if cls_node not in self.graph: return []
        # DFS on inherits edges
        visited = set()
        stack = [cls_node]
        while stack:
            curr = stack.pop()
            if curr in visited: continue
            visited.add(curr)
            
            # Check methods of curr class
            curr_path = self.graph.nodes[curr]["path"]
            curr_qual = self.graph.nodes[curr]["qualified_name"]
            meth_node = f"function:{curr_path}:{curr_qual}.{method_name}"
            if meth_node in self.graph:
                return [(meth_node, res_type, 1.0)]
                
            # Queue bases
            for _, dst, data in self.graph.out_edges(curr, data=True):
                if data.get("relation") == "inherits":
                    stack.append(dst)
        return []

    def _resolve_name(self, name, current_path):
        # 3. Bare name defined in same file
        if "." not in name:
            fn_node = f"function:{current_path}:{name}"
            if fn_node in self.graph: return [(fn_node, "same_file", 1.0)]
            cls_node = f"class:{current_path}:{name}"
            if cls_node in self.graph: return [(cls_node, "same_file", 1.0)]
            
        # 4. Imported name
        file_imports = self.files[current_path].get("imports", [])
        for imp in file_imports:
            # Check exact alias match
            if imp["alias"] == name or imp["name"] == name:
                # Resolve to the module it came from
                mod = imp["module"]
                if mod:
                    # It's `from mod import name`
                    # We don't have deep module resolution here, but we can search globally for this qualname
                    cands = self.func_by_name.get(imp["name"], []) + self.class_by_name.get(imp["name"], [])
                    # filter by those whose path matches the module
                    filtered = [c for c in cands if mod.replace(".", "/") in self.node_to_file[c]]
                    if len(filtered) == 1:
                        return [(filtered[0], "import", 1.0)]
                    elif len(filtered) > 1:
                        return [(c, "ambiguous", 0.5) for c in filtered]
                    
        # 5. Qualified (Class.method or module.func)
        if "." in name:
            cands = self.func_by_qualname.get(name, [])
            if len(cands) == 1: return [(cands[0], "qualified", 1.0)]
            elif len(cands) > 1: return [(c, "ambiguous", 0.5) for c in cands]
            
        # 6. Unique repo-wide
        cands = self.func_by_name.get(name, []) + self.class_by_name.get(name, [])
        if len(cands) == 1:
            return [(cands[0], "unique", 0.8)]
            
        # 7. Ambiguous
        if len(cands) > 1:
            return [(c, "ambiguous", 0.5) for c in cands]
            
        # 8. External (only for imported names, or if dotted)
        # Actually, prompt says: "8. resolves to a third-party/stdlib import: External node"
        # "9. anything else ... NO node and NO edge; just increment unresolved_calls"
        if "." in name or any(imp["alias"] == name or imp["name"] == name for imp in file_imports):
            return [(f"external:{name}", "external", 1.0)]
            
        return []

    def summary(self):
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges()
        }
