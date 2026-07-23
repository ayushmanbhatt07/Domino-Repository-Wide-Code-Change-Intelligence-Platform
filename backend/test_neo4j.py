from neo4j import GraphDatabase
from config import *

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
)

with driver.session(database=NEO4J_DATABASE) as session:

    result = session.run(
        "RETURN 'Connected to Domino Database!' AS msg"
    )

    print(result.single()["msg"])

driver.close()