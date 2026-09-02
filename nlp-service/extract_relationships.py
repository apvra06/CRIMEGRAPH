"""
Relationship extraction for the crime network analysis prototype.

Takes the entity list produced by extract_entities.py and derives
relationships based on co-occurrence within the same report. This is a
deliberately simple heuristic (real relation extraction would use
dependency parsing or a trained relation classifier), but it is
transparent, debuggable, and good enough to populate a demo-scale graph:

  PERSON  + PERSON   -> ASSOCIATED_WITH
  PERSON  + LOCATION -> PRESENT_AT
  PERSON  + ORGANIZATION -> MEMBER_OF
  PERSON  + VEHICLE  -> OWNS_VEHICLE
  PERSON  + PHONE    -> HAS_PHONE
"""
import json
from itertools import combinations

RELATION_RULES = {
    frozenset(["PERSON", "PERSON"]): "ASSOCIATED_WITH",
    frozenset(["PERSON", "LOCATION"]): "PRESENT_AT",
    frozenset(["PERSON", "ORGANIZATION"]): "MEMBER_OF",
    frozenset(["PERSON", "VEHICLE"]): "OWNS_VEHICLE",
    frozenset(["PERSON", "PHONE"]): "HAS_PHONE",
}

def derive_relationships(report):
    entities = report["entities"]
    relationships = []
    for e1, e2 in combinations(entities, 2):
        t1, t2 = e1.get("resolved_text", e1["text"]), e2.get("resolved_text", e2["text"])
        if t1 == t2:
            continue
        label_pair = frozenset([e1["label"], e2["label"]])
        rel_type = RELATION_RULES.get(label_pair)
        if not rel_type:
            continue
        if e1["label"] != "PERSON" and e2["label"] == "PERSON":
            e1, e2, t1, t2 = e2, e1, t2, t1
        relationships.append({
            "source": t1, "source_type": e1["label"],
            "target": t2, "target_type": e2["label"],
            "type": rel_type, "source_document": report["doc_id"], "date": report["date"],
        })
    return relationships

def process_all(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        reports = json.load(f)

    all_relationships = []
    for report in reports:
        all_relationships.extend(derive_relationships(report))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_relationships, f, indent=2)

    return all_relationships

if __name__ == "__main__":
    rels = process_all("extracted_entities.json", "extracted_relationships.json")
    print(f"Derived {len(rels)} relationships -> extracted_relationships.json\n")
    for r in rels[:8]:
        print(f"  ({r['source']}) -[{r['type']}]-> ({r['target']})   [from {r['source_document']}]")

    # Quick sanity check: count relationship types
    from collections import Counter
    counts = Counter(r["type"] for r in rels)
    print("\nRelationship type breakdown:")
    for rel_type, count in counts.most_common():
        print(f"  {rel_type}: {count}")
