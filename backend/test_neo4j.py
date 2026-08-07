from neo4j import GraphDatabase
import config

driver = GraphDatabase.driver(
    config.NEO4J_URI,
    auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
)

with driver.session(database=config.NEO4J_DATABASE) as session:
    result = session.run("RETURN 'Connected to Neo4j' AS msg")
    print(result.single()["msg"])

driver.close()