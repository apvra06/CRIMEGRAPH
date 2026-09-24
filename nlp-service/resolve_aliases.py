"""
Resolves name variants and handles to canonical entity names before
relationship derivation. This is the actual data-cleaning step the
problem statement asks for — without it, the same person fragments
into multiple disconnected Person nodes across sources.

In production this would query the criminal history / master-suspect
database for known aliases. Here it uses the alias table the mock data
generator wrote out (same technique, smaller lookup).
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def load_alias_map(path=None):
    if path is None:
        path = PROJECT_ROOT / "data" / "mock" / "alias_ground_truth.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    alias_to_canonical = {}
    for canonical, value in data.items():
        if canonical == "_handles":
            for name, handle in value.items():
                alias_to_canonical[handle] = name
        else:
            for variant in value:
                alias_to_canonical[variant] = canonical
    return alias_to_canonical

def normalize_phone(raw):
    """Strips +91 / spaces / dashes so the same number always resolves to
    the same PhoneNumber node regardless of source formatting."""
    digits = re.sub(r"[\s-]", "", raw)
    digits = re.sub(r"^\+?91", "", digits)
    return digits

def resolve_entities(extracted_docs, alias_map):
    for doc in extracted_docs:
        for ent in doc["entities"]:
            if ent["label"] == "PERSON":
                raw_text = ent["text"]

                # Surveillance reports may prefix a person's name with
                # "Subject". Remove that reporting label before resolution.
                lookup_text = re.sub(
                    r"^\s*Subject\s+",
                    "",
                    raw_text,
                    flags=re.IGNORECASE
                ).strip()

                if lookup_text in alias_map:
                    ent["resolved_text"] = alias_map[lookup_text]
                    ent["original_text"] = raw_text
                else:
                    ent["resolved_text"] = lookup_text

            elif ent["label"] == "PHONE":
                ent["resolved_text"] = normalize_phone(ent["text"])
                ent["original_text"] = ent["text"]

            else:
                ent["resolved_text"] = ent["text"]

    return extracted_docs

def main():
    with open("extracted_entities.json", encoding="utf-8") as f:
        docs = json.load(f)
    alias_map = load_alias_map()
    resolved = resolve_entities(docs, alias_map)
    with open("extracted_entities.json", "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2)

    resolved_count = sum(1 for d in resolved for e in d["entities"] if e.get("original_text"))
    print(f"Resolved {resolved_count} variant/handle/formatted mentions to canonical form.")

if __name__ == "__main__":
    main()