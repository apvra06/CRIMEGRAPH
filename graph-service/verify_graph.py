from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
)

with driver.session() as session:
    queries = {
        "Nodes": "MATCH (n) RETURN count(n) AS count",
        "Relationships": "MATCH ()-[r]->() RETURN count(r) AS count",
        "Persons": "MATCH (n:Person) RETURN count(n) AS count",
        "Phones": "MATCH (n:PhoneNumber) RETURN count(n) AS count",
        "Called": "MATCH ()-[r:CALLED]->() RETURN count(r) AS count",
        "Transactions": "MATCH ()-[r:TRANSACTED_WITH]->() RETURN count(r) AS count",
        "Known associates": "MATCH ()-[r:KNOWN_ASSOCIATE_OF]->() RETURN count(r) AS count"
    }

    for label, query in queries.items():
        print(f"{label}: {session.run(query).single()['count']}")

driver.close()
