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
