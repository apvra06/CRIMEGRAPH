"""
Loads structured criminal history records directly into Neo4j.

Unlike FIR/surveillance/social/intel data, this doesn't need NLP — it's
already structured JSON. Adds:
  - priorConvictions / lastCaseId properties on Person nodes
  - KNOWN_ASSOCIATE_OF relationships between Person nodes

Run this alongside load_structured_data.py, after load_graph.py has
created the base Person nodes (MERGE will still create them if they
don't exist yet, but running load_graph.py first keeps entity data
consistent with the rest of the pipeline).
"""
import json
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

CRIMINAL_HISTORY_PATH = "../data/mock/criminal_history.json"


def load_criminal_history(tx, records):
    for rec in records:
        tx.run("""
            MERGE (p:Person {name: $name})
            SET p.priorConvictions = $convictions, p.lastCaseId = $case_id
        """, name=rec["name"], convictions=rec["prior_convictions"],
             case_id=rec["last_case_id"])

        for associate in rec["known_associates"]:
            tx.run("""
                MERGE (a:Person {name: $name})
                MERGE (b:Person {name: $associate})
                MERGE (a)-[r:KNOWN_ASSOCIATE_OF]->(b)
                SET r.source_document = $case_id
            """, name=rec["name"], associate=associate, case_id=rec["last_case_id"])


def read_records(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    records = read_records(CRIMINAL_HISTORY_PATH)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()  # fails fast with a clear error if creds/URI are wrong

    with driver.session() as session:
        session.execute_write(load_criminal_history, records)

    driver.close()
    print(f"Loaded criminal history for {len(records)} person(s), "
          f"including priorConvictions/lastCaseId properties and "
          f"KNOWN_ASSOCIATE_OF relationships.")


if __name__ == "__main__":
    main()
