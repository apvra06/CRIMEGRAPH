"""
Single entry point that routes every source file to the right pipeline:
narrative sources -> spaCy extract_entities -> resolve_aliases -> extract_relationships
structured sources -> direct field mapping (handled in graph-service loaders)

This replaces calling extract_entities.py / resolve_aliases.py /
extract_relationships.py separately per file — one command processes
everything, tags every extracted entity with its source_type for
provenance, and resolves name variants/handles to canonical identity
BEFORE relationships get derived (skipping this step means the same
person fragments into multiple disconnected Person nodes downstream).
"""
import json
import sys
sys.path.append("../data/schema")
from source_record import SourceType

from extract_entities import build_pipeline, extract_entities
from resolve_aliases import load_alias_map, resolve_entities
from extract_relationships import derive_relationships

NARRATIVE_FILES = {
    SourceType.FIR: "../data/mock/fir_reports.json",
    SourceType.SURVEILLANCE: "../data/mock/surveillance_reports.json",
    SourceType.SOCIAL_MEDIA: "../data/mock/social_media_posts.json",
    SourceType.INTEL_REPORT: "../data/mock/intel_reports.json",
}


def process_narrative_source(nlp, source_type, path):
    with open(path, encoding="utf-8") as f:
        docs = json.load(f)
    results = []
    for doc in docs:
        entities = extract_entities(nlp, doc["text"])
        results.append({
            "doc_id": doc["doc_id"],
            "date": doc["date"],
            "text": doc["text"],
            "source_type": source_type.value,
            "entities": entities,
        })
    return results


def main():
    nlp = build_pipeline()
    all_extracted = []
    for source_type, path in NARRATIVE_FILES.items():
        try:
            extracted = process_narrative_source(nlp, source_type, path)
            print(f"{source_type.value}: {len(extracted)} docs processed")
            all_extracted.extend(extracted)
        except FileNotFoundError:
            print(f"{source_type.value}: {path} not found, skipping")

    # Resolve name variants and phone-format inconsistencies to canonical
    # identity BEFORE relationships get derived, so co-occurrence pairs
    # like ("R. Sharma", "Rahul Sharma") collapse into one node instead
    # of creating a phantom extra person in the graph.
    alias_map = load_alias_map()
    all_extracted = resolve_entities(all_extracted, alias_map)
    resolved_count = sum(
        1 for d in all_extracted for e in d["entities"] if e.get("original_text")
    )
    print(f"Resolved {resolved_count} variant/handle/formatted mentions to canonical form.")

    with open("extracted_entities.json", "w", encoding="utf-8") as f:
        json.dump(all_extracted, f, indent=2)

    all_relationships = []
    for doc in all_extracted:
        all_relationships.extend(derive_relationships(doc))

    with open("extracted_relationships.json", "w", encoding="utf-8") as f:
        json.dump(all_relationships, f, indent=2)

    print(f"\nTotal: {len(all_extracted)} docs -> {len(all_relationships)} relationships")


if __name__ == "__main__":
    main()