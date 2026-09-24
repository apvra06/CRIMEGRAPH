from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
)

with driver.session() as session:
    query = """
    MATCH (p:Person)
    WHERE p.name IN ["Saxena", "Subject Arjun Patel", "Subject Neeraj Sharma"]
    OPTIONAL MATCH (p)-[r]-(n)
    RETURN p.name AS person,
           type(r) AS rel,
           labels(n) AS neighbor_labels,
           n.name AS neighbor
    ORDER BY person
    """

    for record in session.run(query):
        print(record)

driver.close()
