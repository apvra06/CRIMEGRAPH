"""
Relationship extraction for the crime network analysis prototype.

Takes the entity list produced by extract_entities.py and derives
relationships based on co-occurrence within the same report.

Most relationships use transparent co-occurrence heuristics, while
PERSON + PHONE relationships use simple phrase-aware rules so that
ownership/contact information is not confused with incoming calls.

Supported relationships:

  PERSON  + PERSON   -> ASSOCIATED_WITH
  PERSON  + LOCATION -> PRESENT_AT
  PERSON  + ORGANIZATION -> MEMBER_OF
  PERSON  + VEHICLE  -> OWNS_VEHICLE
  PERSON  + PHONE    -> HAS_PHONE / RECEIVED_CALL_FROM
"""

import json
import re
from itertools import combinations


RELATION_RULES = {
    frozenset(["PERSON", "PERSON"]): "ASSOCIATED_WITH",
    frozenset(["PERSON", "LOCATION"]): "PRESENT_AT",
    frozenset(["PERSON", "ORGANIZATION"]): "MEMBER_OF",
    frozenset(["PERSON", "VEHICLE"]): "OWNS_VEHICLE",
    frozenset(["PERSON", "PHONE"]): "HAS_PHONE",
}


def normalize_phone(value):
    """Return the last 10 digits of a phone number."""
    digits = re.sub(r"\D", "", value)
    return digits[-10:] if len(digits) >= 10 else digits


def is_received_call_from(report_text, phone):
    """
    Detect phrases where the person received an incoming call from
    the extracted phone number.

    Example:
        'V. Mehra received a call from +919876543210'
    """

    normalized_phone = normalize_phone(phone)

    if not normalized_phone:
        return False

    phone_variants = [
        re.escape(normalized_phone),
        re.escape("+91" + normalized_phone),
        re.escape("+91 " + normalized_phone),
        re.escape("+91-" + normalized_phone),
    ]

    phone_pattern = "(?:" + "|".join(phone_variants) + ")"

    pattern = (
        r"\breceived\s+(?:a\s+)?call\s+from\s+"
        + phone_pattern
        + r"\b"
    )

    return re.search(pattern, report_text, re.IGNORECASE) is not None


def derive_relationships(report):
    entities = report["entities"]
    relationships = []
    report_text = report.get("text", "")

    for e1, e2 in combinations(entities, 2):
        t1 = e1.get("resolved_text", e1["text"])
        t2 = e2.get("resolved_text", e2["text"])

        if t1 == t2:
            continue

        label_pair = frozenset([e1["label"], e2["label"]])

        # ------------------------------------------------------------
        # Special handling for PERSON + PHONE.
        #
        # We distinguish:
        #   "contacted 9345678901"
        #       -> HAS_PHONE
        #
        #   "received a call from 9345678901"
        #       -> RECEIVED_CALL_FROM
        #
        # This prevents incoming-call numbers from being incorrectly
        # interpreted as the person's own phone number.
        # ------------------------------------------------------------
        if label_pair == frozenset(["PERSON", "PHONE"]):

            if e1["label"] == "PERSON":
                person = t1
                phone = t2
            else:
                person = t2
                phone = t1

            if is_received_call_from(report_text, phone):
                rel_type = "RECEIVED_CALL_FROM"
            else:
                rel_type = "HAS_PHONE"

            relationships.append({
                "source": person,
                "source_type": "PERSON",
                "target": phone,
                "target_type": "PHONE",
                "type": rel_type,
                "source_document": report["doc_id"],
                "date": report["date"],
            })

            continue

        # ------------------------------------------------------------
        # Existing generic relationship rules.
        # ------------------------------------------------------------
        rel_type = RELATION_RULES.get(label_pair)

        if not rel_type:
            continue

        if e1["label"] != "PERSON" and e2["label"] == "PERSON":
            e1, e2, t1, t2 = e2, e1, t2, t1

        relationships.append({
            "source": t1,
            "source_type": e1["label"],
            "target": t2,
            "target_type": e2["label"],
            "type": rel_type,
            "source_document": report["doc_id"],
            "date": report["date"],
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
    rels = process_all(
        "extracted_entities.json",
        "extracted_relationships.json"
    )

    print(
        f"Derived {len(rels)} relationships "
        f"-> extracted_relationships.json\n"
    )

    for r in rels[:8]:
        print(
            f"  ({r['source']}) -[{r['type']}]-> "
            f"({r['target']}) "
            f"[from {r['source_document']}]"
        )

    from collections import Counter

    counts = Counter(r["type"] for r in rels)

    print("\nRelationship type breakdown:")

    for rel_type, count in counts.most_common():
        print(f"  {rel_type}: {count}")