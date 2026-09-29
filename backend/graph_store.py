from neo4j import GraphDatabase
import config
from collections import defaultdict
import datetime
import networkx as nx

class Neo4jGraphStore:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()
        
    def ensure_schema(self):
        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            labels = ["File", "Class", "Function", "Route", "External", "Repo"]
            for label in labels:
                session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE (n.repo, n.id) IS UNIQUE")
                session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.repo, n.name)")
                session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.repo, n.qualified_name)")

    def save(self, repo: str, graph: nx.DiGraph):
        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            session.execute_write(self._replace_repo_tx, repo, graph)

    @staticmethod
    def _replace_repo_tx(tx, repo: str, graph: nx.DiGraph):
        # 1. Remove old graph and repo metadata
        tx.run("MATCH (n) WHERE n.repo = $repo DETACH DELETE n", repo=repo)
        
        # 2. Write Nodes in batches grouped by label
        nodes_by_label = defaultdict(list)
        for node_id, data in graph.nodes(data=True):
            label = data.get("type", "Entity").capitalize()
            props = dict(data)
            props["id"] = node_id
            props["repo"] = repo
            nodes_by_label[label].append(props)
            
        for label, nodes in nodes_by_label.items():
            for i in range(0, len(nodes), 1000):
                batch = nodes[i:i+1000]
                tx.run(f"""
                UNWIND $batch AS props
                MERGE (n:{label} {{repo: $repo, id: props.id}})
                SET n = props
                """, batch=batch, repo=repo)
                
        # 3. Write Edges in batches grouped by relation
        edges_by_rel = defaultdict(list)
        for source, target, data in graph.edges(data=True):
            rel = data.get("relation", "RELATED").upper()
            edges_by_rel[rel].append({
                "source": source,
                "target": target,
                "props": dict(data)
            })
            
        for rel, edges in edges_by_rel.items():
            for i in range(0, len(edges), 1000):
                batch = edges[i:i+1000]
                tx.run(f"""
                UNWIND $batch AS edge
                MATCH (a {{repo: $repo, id: edge.source}})
                MATCH (b {{repo: $repo, id: edge.target}})
                MERGE (a)-[r:{rel}]->(b)
                SET r = edge.props
                """, batch=batch, repo=repo)
                
        # 4. Write Repo metadata node
        commit_sha = graph.graph.get("commit_sha", "unknown")
        analyzed_at = graph.graph.get("analyzed_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
        parse_errors = graph.graph.get("parse_errors", 0)
        unresolved = sum(d.get("unresolved_calls", 0) for _, d in graph.nodes(data=True))
        
        tx.run("""
        MERGE (r:Repo {repo: $repo, id: $repo})
        SET r.name = $repo,
            r.commit_sha = $commit_sha,
            r.analyzed_at = $analyzed_at,
            r.node_count = $nodes,
            r.edge_count = $edges,
            r.unresolved_call_count = $unresolved,
            r.parse_errors = $parse_errors
        """, repo=repo, commit_sha=commit_sha, analyzed_at=analyzed_at, 
        nodes=graph.number_of_nodes(), edges=graph.number_of_edges(),
        unresolved=unresolved, parse_errors=parse_errors)

    def list_repos(self):
        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            res = session.run("MATCH (r:Repo) RETURN properties(r) AS p")
            return [record["p"] for record in res]

    def repo_summary(self, repo: str):
        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            res = session.run("MATCH (r:Repo {repo: $repo}) RETURN properties(r) AS p", repo=repo)
            rec = res.single()
            return rec["p"] if rec else None

    def find_entities(self, repo: str, type=None, name=None, qualified_name=None, path=None, method=None, route_path=None, limit=50):
        query = "MATCH (n {repo: $repo}) "
        where_clauses = []
        params = {"repo": repo, "limit": limit}
        
        if type:
            query = f"MATCH (n:{type.capitalize()} {{repo: $repo}}) "
        if name:
            where_clauses.append("n.name = $name")
            params["name"] = name
        if qualified_name:
            where_clauses.append("n.qualified_name = $qualified_name")
            params["qualified_name"] = qualified_name
        if path:
            where_clauses.append("n.path = $path")
            params["path"] = path
        if method:
            where_clauses.append("n.method = $method")
            params["method"] = method
        if route_path:
            where_clauses.append("n.route_path = $route_path")
            params["route_path"] = route_path
            
        if where_clauses:
            query += "WHERE " + " AND ".join(where_clauses) + " "
            
        query += "RETURN properties(n) AS p LIMIT $limit"
        
        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            res = session.run(query, **params)
            return [record["p"] for record in res]

    def get_nodes(self, repo: str, ids: list[str]):
        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            res = session.run("""
            UNWIND $ids AS id
            MATCH (n {repo: $repo, id: id})
            RETURN properties(n) AS p
            """, repo=repo, ids=ids)
            return [record["p"] for record in res]

    def neighbors(self, repo: str, ids: list[str], direction: str, rel_types: list[str] = None, min_confidence: float = 0.0):
        # direction: 'out', 'in', or 'both'
        arrow_left = "<-" if direction in ['in', 'both'] else "-"
        arrow_right = "->" if direction in ['out', 'both'] else "-"
        
        rel_str = ""
        if rel_types:
            rel_str = ":" + "|".join(rel_types)
            
        query = f"""
        UNWIND $ids AS id
        MATCH (a {{repo: $repo, id: id}}){arrow_left}[r{rel_str}]{arrow_right}(b {{repo: $repo}})
        WHERE coalesce(r.confidence, 1.0) >= $min_confidence
        RETURN a.id AS src, type(r) AS rel, b.id AS dst, properties(r) AS props
        """
        
        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            res = session.run(query, repo=repo, ids=ids, min_confidence=min_confidence)
            return [{"src": rec["src"], "rel": rec["rel"], "dst": rec["dst"], "props": rec["props"]} for rec in res]

    def load_repo_graph(self, repo: str) -> nx.DiGraph:
        g = nx.DiGraph()
        with self.driver.session(database=config.NEO4J_DATABASE) as session:
            nodes = session.run("MATCH (n {repo: $repo}) WHERE NOT n:Repo RETURN properties(n) AS p", repo=repo)
            for rec in nodes:
                p = rec["p"]
                g.add_node(p["id"], **p)
                
            edges = session.run("MATCH (a {repo: $repo})-[r]->(b {repo: $repo}) RETURN a.id AS src, b.id AS dst, properties(r) AS p", repo=repo)
            for rec in edges:
                g.add_edge(rec["src"], rec["dst"], **rec["p"])
        return g
        
    # Keep old methods for compatibility until tests are rewritten
    def find_function(self, repo: str, function_name: str):
        res = self.find_entities(repo, type="Function", name=function_name, limit=1)
        return res[0] if res else None

    def find_file(self, repo: str, file_name: str):
        res = self.find_entities(repo, type="File", name=file_name, limit=1)
        return res[0] if res else None

    def find_class(self, repo: str, class_name: str):
        res = self.find_entities(repo, type="Class", name=class_name, limit=1)
        return res[0] if res else None

    def find_route(self, repo: str, route: str):
        res = self.find_entities(repo, type="Route", path=route, limit=1)
        return res[0] if res else None

    def find_entity(self, repo: str, entity_type: str, name: str):
        if entity_type == "route":
            return self.find_route(repo, name)
        elif entity_type == "function":
            return self.find_function(repo, name)
        elif entity_type == "class":
            return self.find_class(repo, name)
        elif entity_type == "file":
            return self.find_file(repo, name)
        else:
            raise ValueError(f"Unsupported entity type: {entity_type}")

    def find_downstream(self, repo: str, node_id: str, depth: int = 3):
        # BFS
        visited = set()
        queue = [(node_id, 0)]
        result_ids = set()
        
        while queue:
            curr_id, d = queue.pop(0)
            if d >= depth:
                continue
            edges = self.neighbors(repo, [curr_id], direction='out')
            for e in edges:
                dst = e['dst']
                if dst not in visited:
                    visited.add(dst)
                    result_ids.add(dst)
                    queue.append((dst, d+1))
                    
        return self.get_nodes(repo, list(result_ids))