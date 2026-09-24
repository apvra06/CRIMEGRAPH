from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
)

with driver.session() as session:
    result = session.run("""
        MATCH (n)
        DETACH DELETE n
        RETURN count(n) AS deleted
    """)
    print("Deleted:", result.single()["deleted"], "nodes")

driver.close()
