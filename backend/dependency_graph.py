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
