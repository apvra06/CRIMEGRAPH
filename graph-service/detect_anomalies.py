"""
Anomaly detection for the crime network analysis prototype.

Flags two patterns directly from the raw CDR/transaction CSVs (no ML
needed — simple, explainable statistics are the right tool here):

  1. Call frequency spikes: a phone number making unusually many calls
     compared to the rest of the network (mean + 2*std threshold).
  2. Transaction structuring: repeated transactions just under a common
     reporting threshold (₹50,000), a classic money-laundering signature.

Flags are written back onto the relevant Person/PhoneNumber nodes in
Neo4j so the Streamlit dashboard (Phase 6) can query them directly
without recomputing anything.
"""
import csv
from collections import Counter
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

CDR_PATH = "../data/mock/cdr.csv"
TRANSACTIONS_PATH = "../data/mock/transactions.csv"

STRUCTURING_THRESHOLD = 50000
STRUCTURING_BAND = 5000  # flag transactions within this band below the threshold


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def detect_call_spikes(cdr_rows):
    call_counts = Counter(row["caller_number"] for row in cdr_rows)
    counts = list(call_counts.values())
    mean = sum(counts) / len(counts)
    variance = sum((c - mean) ** 2 for c in counts) / len(counts)
    std = variance ** 0.5
    threshold = mean + 2 * std

    flagged = {number: count for number, count in call_counts.items() if count > threshold}
    return flagged, mean, std, threshold


def detect_structuring(txn_rows):
    """Flags people who repeatedly send amounts just under the reporting
    threshold — a single such transaction could be innocent, but a PATTERN
    of repeated near-threshold amounts from the same sender is the actual
    red flag, so we require at least 2 occurrences."""
    near_threshold_counts = Counter()
    for row in txn_rows:
        amount = float(row["amount"])
        if STRUCTURING_THRESHOLD - STRUCTURING_BAND <= amount < STRUCTURING_THRESHOLD:
            near_threshold_counts[row["sender_name"]] += 1

    flagged = {name: count for name, count in near_threshold_counts.items() if count >= 2}
    return flagged


def write_flags_to_neo4j(call_flags, structuring_flags):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    with driver.session() as session:
        for number, count in call_flags.items():
            session.run("""
                MATCH (p:PhoneNumber {name: $number})
                SET p.anomalyFlag = 'CALL_SPIKE', p.anomalyCallCount = $count
            """, number=number, count=count)

        for name, count in structuring_flags.items():
            session.run("""
                MATCH (p:Person {name: $name})
                SET p.anomalyFlag = 'STRUCTURING', p.anomalyTxnCount = $count
            """, name=name, count=count)

    driver.close()


def main():
    cdr_rows = read_csv(CDR_PATH)
    txn_rows = read_csv(TRANSACTIONS_PATH)

    call_flags, mean, std, threshold = detect_call_spikes(cdr_rows)
    print(f"Call frequency: mean={mean:.1f}, std={std:.1f}, threshold={threshold:.1f}")
    print(f"Flagged {len(call_flags)} number(s) for call spikes:")
    for number, count in call_flags.items():
        print(f"  {number}: {count} calls made (threshold: {threshold:.1f})")

    structuring_flags = detect_structuring(txn_rows)
    print(f"\nFlagged {len(structuring_flags)} sender(s) for transaction structuring:")
    for name, count in structuring_flags.items():
        print(f"  {name}: {count} transactions just under ₹{STRUCTURING_THRESHOLD}")

    write_flags_to_neo4j(call_flags, structuring_flags)
    print("\nFlags written to Neo4j (PhoneNumber.anomalyFlag / Person.anomalyFlag).")


if __name__ == "__main__":
    main()
