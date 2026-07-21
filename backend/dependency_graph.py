from pathlib import Path
import networkx as nx


class DependencyGraphBuilder:
    """
    Builds a repository dependency graph from the output
    produced by RepositoryAnalyzer.

    Graph Type:
        Directed Graph (DiGraph)

    Why Directed?
    --------------------
    Relationships have directions.

    project.py ----contains----> create_book()

    create_book() ----calls----> get_db()

    project.py ----imports----> database.py
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    # -------------------------------------------------
    # Add File Nodes
    # -------------------------------------------------
    def _add_files(self, analysis):

        """
        Creates one node for every file.

        Example

        Node:
        id = file:project.py

        Attributes:
            type = file
            name = project.py
        """

        for file in analysis["files"]:

            self.graph.add_node(
                f"file:{file['path']}",
                type="file",
                name=file["path"]
            )

    # -------------------------------------------------
    # Add Function Nodes
    # -------------------------------------------------
    def _add_functions(self, analysis):

        """
        Creates function nodes and connects

        File
            |
         contains
            |
        Function
        """

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

                self.graph.add_edge(
                    file_node,
                    function_node,
                    relation="contains"
                )

    # -------------------------------------------------
    # Add Class Nodes
    # -------------------------------------------------
    def _add_classes(self, analysis):

        """
        File
            |
        contains
            |
        Class
        """

        for file in analysis["files"]:

            file_node = f"file:{file['path']}"

            for cls in file.get("classes", []):

                class_node = f"class:{file['path']}:{cls['name']}"

                self.graph.add_node(
                    class_node,
                    type="class",
                    name=cls["name"]
                )

                self.graph.add_edge(
                    file_node,
                    class_node,
                    relation="contains"
                )

    # -------------------------------------------------
    # Add Route Nodes
    # -------------------------------------------------
    def _add_routes(self, analysis):

        """
        Route
            |
        handled_by
            |
        Function
        """

        for file in analysis["files"]:

            functions = file.get("functions", [])
            routes = file.get("routes", [])

            # Simple assumption:
            # route i belongs to function i
            for route, function in zip(routes, functions):

                route_node = f"route:{route['method']}:{route['path']}"

                function_node = (
                    f"function:{file['path']}:{function['name']}"
                )

                self.graph.add_node(
                    route_node,
                    type="route",
                    method=route["method"],
                    path=route["path"]
                )

                self.graph.add_edge(
                    route_node,
                    function_node,
                    relation="handled_by"
                )

    # -------------------------------------------------
    # Add Function Calls
    # -------------------------------------------------
    def _add_calls(self, analysis):

        """
        Function

           calls

        Another Function

        NOTE:
        Currently we only know the NAME being called.

        Stage 4 will resolve these calls to the actual
        function definitions across files.
        """

        for file in analysis["files"]:

            current_file = file["path"]

            for function in file.get("functions", []):

                source = (
                    f"function:{current_file}:{function['name']}"
                )

                for call in function.get("calls", []):

                    target = f"external:{call}"

                    self.graph.add_node(
                        target,
                        type="external_call",
                        name=call
                    )

                    self.graph.add_edge(
                        source,
                        target,
                        relation="calls"
                    )

    # -------------------------------------------------
    # Build Graph
    # -------------------------------------------------
    def build(self, analysis):

        """
        Main Entry Point.
        """

        self._add_files(analysis)

        self._add_functions(analysis)

        self._add_classes(analysis)

        self._add_routes(analysis)

        self._add_calls(analysis)

        return self.graph

    # -------------------------------------------------
    # Summary
    # -------------------------------------------------
    def summary(self):

        return {

            "nodes": self.graph.number_of_nodes(),

            "edges": self.graph.number_of_edges()
        }

    # -------------------------------------------------
    # Export
    # -------------------------------------------------
    def export_graphml(self, output_path: str):

        """
        Saves the graph.

        GraphML can later be opened in:

        - Neo4j Import
        - Gephi
        - Cytoscape
        - yEd
        """

        nx.write_graphml(self.graph, output_path)