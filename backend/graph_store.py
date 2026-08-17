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