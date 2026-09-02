"""
Loads structured CDR and financial transaction data directly into Neo4j.

Unlike FIR reports, this data is already structured (CSV), so it doesn't
need the NLP extraction pipeline — we parse and load it straight in.

Adds:
  - CALLED relationships between PhoneNumber nodes, from cdr.csv
  - TRANSACTED_WITH relationships between Person nodes, from transactions.csv

Run this AFTER load_graph.py, so the Person/PhoneNumber nodes referenced
here already exist (MERGE will still create them if not, but running
load_graph.py first keeps entity data consistent).
"""
import csv
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

CDR_PATH = "../data/mock/cdr.csv"
TRANSACTIONS_PATH = "../data/mock/transactions.csv"


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_calls(tx, rows):
    for row in rows:
        # Each distinct (caller, receiver, timestamp) becomes its own edge,
        # since the same two numbers can call each other many times — we
        # want that frequency to show up for anomaly detection later.
        tx.run("""
            MERGE (a:PhoneNumber {name: $caller})
            MERGE (b:PhoneNumber {name: $receiver})
            MERGE (a)-[r:CALLED {timestamp: $ts}]->(b)
            SET r.duration_sec = $duration, r.tower_location = $tower
        """, caller=row["caller_number"], receiver=row["receiver_number"],
             ts=row["timestamp"], duration=int(row["duration_sec"]),
             tower=row["tower_location"])


def load_transactions(tx, rows):
    for row in rows:
        tx.run("""
            MERGE (a:Person {name: $sender})
            MERGE (b:Person {name: $receiver})
            MERGE (a)-[r:TRANSACTED_WITH {timestamp: $ts, amount: $amount}]->(b)
            SET r.transaction_type = $ttype
        """, sender=row["sender_name"], receiver=row["receiver_name"],
             ts=row["timestamp"], amount=float(row["amount"]),
             ttype=row["transaction_type"])


def main():
    cdr_rows = read_csv(CDR_PATH)
    txn_rows = read_csv(TRANSACTIONS_PATH)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    with driver.session() as session:
        session.execute_write(load_calls, cdr_rows)
        session.execute_write(load_transactions, txn_rows)

    driver.close()
    print(f"Loaded {len(cdr_rows)} CALLED relationships and "
          f"{len(txn_rows)} TRANSACTED_WITH relationships into Neo4j.")


if __name__ == "__main__":
    main()
