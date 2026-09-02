"""
Entity extraction pipeline for the crime network analysis prototype.

Reads FIR-style (and now surveillance/social/intel) text reports and extracts:
  - PERSON   (spaCy's built-in NER + known-people gazetteer + alias/handle gazetteer)
  - GPE/LOC  (spaCy's built-in NER, mapped to LOCATION)
  - ORG      (spaCy's built-in NER)
  - PHONE    (custom regex rule, tolerant of +91 / spaces / dashes)
  - VEHICLE  (custom regex rule)

Outputs structured JSON: one record per report, with a list of
{text, label} entities, ready to feed into resolve_aliases.py and then
the graph-service ETL step.
"""
import json
import os
import spacy
from spacy.pipeline import EntityRuler

# Known locations/orgs used across our mock data. In a real deployment this
# would be a maintained gazetteer table (e.g. a list of known localities from
# police jurisdiction records), not a hardcoded list — but for a prototype,
# a small lookup list fixes most of the code-mixed (Hinglish) NER failures
# without needing a full fine-tuned multilingual model.
KNOWN_PEOPLE = [
    "Rahul Sharma", "Vikram Singh", "Amit Verma", "Suresh Yadav",
    "Deepak Rao", "Manoj Tiwari", "Ravi Kumar", "Sanjay Mehta",
]

KNOWN_LOCATIONS = ["Malviya Nagar", "Rajwada", "Vijay Nagar", "Bhawarkuan", "Sudama Nagar"]
KNOWN_ORGS = ["Shree Traders", "Om Logistics", "Balaji Enterprises"]

# Path to the alias/handle table written by generate_mock_data.py. Loading
# this at pipeline build time means variants like "R. Sharma" and handles
# like "@rahul_47" get registered as PERSON patterns at the SAME tier as
# canonical names — the ruler doesn't care whether a name is "the real one"
# or a variant, it just needs to know it's a name worth tagging. Actually
# collapsing variant -> canonical identity happens later, in
# resolve_aliases.py; this step is only responsible for finding the mention.
ALIAS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "mock", "alias_ground_truth.json"
)


def load_alias_names():
    """Returns (multi_word_variants, single_token_handles).
    Missing file is expected before the mock-data generator has been run
    with the alias export step, so this fails soft rather than crashing
    the whole pipeline."""
    variants = []
    handles = []
    try:
        with open(ALIAS_PATH, encoding="utf-8") as f:
            alias_data = json.load(f)
    except FileNotFoundError:
        return variants, handles

    for canonical, value in alias_data.items():
        if canonical == "_handles":
            handles.extend(value.values())
        else:
            variants.extend(value)
    return variants, handles


def build_pipeline():
    nlp = spacy.load("en_core_web_sm")

    # Add custom rule-based patterns BEFORE the statistical NER component,
    # so phone numbers, vehicle plates, and known locations/orgs are locked
    # in before spaCy's statistical model gets a chance to mislabel them —
    # this is especially important for Hinglish/code-mixed sentences, where
    # the base English model has no training signal to work with.
    if "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", before="ner")
        patterns = [
            # Indian mobile numbers: 10 digits, optionally +91 prefixed,
            # optionally with a space after +91 or a dash splitting the
            # digits (e.g. "9876543210", "+919876543210", "+91 9876543210",
            # "98765-43210"). Real CDR/FIR data mixes these formats, so the
            # extraction rule has to tolerate all of them, not just one.
            {"label": "PHONE", "pattern": [{"TEXT": {"REGEX": r"^(\+?91)?\d{10}$"}}]},
            {"label": "PHONE", "pattern": [
                {"TEXT": {"REGEX": r"^\+?91$"}},
                {"TEXT": {"REGEX": r"^\d{10}$"}},
            ]},
            {"label": "PHONE", "pattern": [{"TEXT": {"REGEX": r"^\d{5}-\d{5}$"}}]},
            # Indian vehicle plates: e.g. MP09AB1234
            {"label": "VEHICLE", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$"}}]},
        ]
        # Multi-word gazetteer entries need token-by-token patterns
        for person in KNOWN_PEOPLE:
            patterns.append({"label": "PERSON", "pattern": [{"TEXT": tok} for tok in person.split()]})
        for loc in KNOWN_LOCATIONS:
            patterns.append({"label": "GPE", "pattern": [{"TEXT": tok} for tok in loc.split()]})
        for org in KNOWN_ORGS:
            patterns.append({"label": "ORG", "pattern": [{"TEXT": tok} for tok in org.split()]})

        # Name variants ("R. Sharma", "Vicky Singh") and social handles
        # ("@rahul_47") from the alias table. Variants are multi-word like
        # canonical names, so they get the same token-by-token pattern.
        # Handles are single unbroken tokens (no internal spaces), so they
        # get a direct TEXT match instead.
        variant_names, handles = load_alias_names()
        for variant in variant_names:
            patterns.append({"label": "PERSON", "pattern": [{"TEXT": tok} for tok in variant.split()]})
        for handle in handles:
            patterns.append({"label": "PERSON", "pattern": [{"TEXT": handle}]})

        ruler.add_patterns(patterns)
    return nlp


LABEL_MAP = {
    "PERSON": "PERSON",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "ORG": "ORGANIZATION",
    "PHONE": "PHONE",
    "VEHICLE": "VEHICLE",
}

# Common Hindi function words that the English statistical NER model
# sometimes misfires on inside code-mixed sentences. This is a stopgap for
# the prototype — a fine-tuned multilingual model (e.g. IndicNER) wouldn't
# need this crutch, but a blocklist gets us most of the accuracy for free.
HINDI_STOPWORDS = {"hai", "the", "gaya", "kiya", "mein", "ka", "aur", "dono"}


def extract_entities(nlp, text):
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        mapped_label = LABEL_MAP.get(ent.label_)
        if not mapped_label:
            continue
        if ent.text.lower() in HINDI_STOPWORDS:
            continue
        # Extra guard for PERSON: real names/handles are capitalized or
        # start with a known symbol ("Vikram Singh", "R.", "@rahul_47").
        # Hindi/Hinglish function-word spans ("mein mile", "dono ka") are
        # lowercase and slip past the statistical model on some spaCy model
        # versions. We allow a token through if EITHER it's alphabetic +
        # title-case (covers canonical names and "Vicky"/"Sharma") OR it
        # starts with '@' or is a single uppercase-letter-plus-period
        # initial (covers handles and "R." style variants).
        if mapped_label == "PERSON":
            tokens = ent.text.split()
            def token_ok(tok):
                if tok.startswith("@"):
                    return True
                if tok.isalpha() and tok.istitle():
                    return True
                if tok.rstrip(".").isalpha() and tok[0].isupper() and len(tok.rstrip(".")) <= 2:
                    return True  # short initials like "R."
                return False
            if not all(token_ok(tok) for tok in tokens):
                continue
        entities.append({"text": ent.text, "label": mapped_label})
    return entities


def process_reports(input_path, output_path):
    nlp = build_pipeline()
    with open(input_path, "r", encoding="utf-8") as f:
        reports = json.load(f)

    results = []
    for report in reports:
        entities = extract_entities(nlp, report["text"])
        results.append({
            "doc_id": report["doc_id"],
            "date": report["date"],
            "text": report["text"],
            "entities": entities,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    results = process_reports("../data/mock/fir_reports.json", "extracted_entities.json")
    print(f"Processed {len(results)} reports -> extracted_entities.json\n")
    # Print a few samples so we can eyeball extraction quality
    for r in results[:5]:
        print(f"[{r['doc_id']}] {r['text']}")
        print(f"  -> {r['entities']}\n")
