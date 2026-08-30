
import json
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Maps our entity labels to Neo4j node labels
LABEL_FOR_TYPE = {
    "PERSON": "Person",
    "LOCATION": "Location",
    "ORGANIZATION": "Organization",
    "VEHICLE": "Vehicle",
    "PHONE": "PhoneNumber",
}


def load_entities(tx, entities):
    """MERGE (not CREATE) so re-running this script doesn't create duplicate
    nodes for the same entity mentioned across multiple reports."""
    for ent in entities:
        label = LABEL_FOR_TYPE.get(ent["label"])
        if not label:
            continue
        tx.run(f"MERGE (n:{label} {{name: $name}})", name=ent["text"])


def load_relationships(tx, relationships):
    for rel in relationships:
        src_label = LABEL_FOR_TYPE.get(rel["source_type"])
        tgt_label = LABEL_FOR_TYPE.get(rel["target_type"])
        if not src_label or not tgt_label:
            continue
        tx.run(f"""
            MERGE (a:{src_label} {{name: $source}})
            MERGE (b:{tgt_label} {{name: $target}})
            MERGE (a)-[r:{rel['type']}]->(b)
            SET r.source_document = $doc, r.date = $date
        """, source=rel["source"], target=rel["target"],
             doc=rel["source_document"], date=rel["date"])


def main():
    with open("../nlp-service/extracted_entities.json", encoding="utf-8") as f:
        reports = json.load(f)
    all_entities = []
    for r in reports:
        all_entities.extend(r["entities"])

    with open("../nlp-service/extracted_relationships.json", encoding="utf-8") as f:
        relationships = json.load(f)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()  # fails fast with a clear error if creds/URI are wrong

    with driver.session() as session:
        session.execute_write(load_entities, all_entities)
        session.execute_write(load_relationships, relationships)

    driver.close()
    print(f"Loaded {len(all_entities)} entity mentions and "
          f"{len(relationships)} relationships into Neo4j.")


if __name__ == "__main__":
    main()
