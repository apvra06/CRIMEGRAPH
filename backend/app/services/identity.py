"""Canonical identity resolution for person aliases in the case graph.

The source graph contains multiple identifiers for the same real-world person.
Keep the canonical full-name representation in UI/API responses while retaining
all source aliases for querying the underlying graph.
"""

from typing import Dict, Iterable, List

# Canonical display name -> all known source identifiers for that person.
CANONICAL_PERSON_ALIASES: Dict[str, List[str]] = {
    "Amit Verma": ["Amit Verma", "A. Verma", "@amit_13"],
    "Rahul Sharma": ["Rahul Sharma", "Rahul S.", "R. Sharma", "@rahul_91"],
    "Sanjay Mehta": ["Sanjay Mehta", "S. Mehta", "Sanjay M.", "@sanjay_23"],
    "Ravi Kumar": ["Ravi Kumar", "R. Kumar", "@ravi_27"],
    "Vikram Singh": ["Vikram Singh","V. Singh","Vicky Singh","@vikram_24",],
    "Suresh Yadav": ["Suresh Yadav", "Suresh Y.", "S. Yadav"],
    "Deepak Rao": ["Deepak Rao", "D. Rao"],
    "Manoj Tiwari": ["Manoj Tiwari", "Manoj T.", "M. Tiwari", "@manoj_38"],
}

# Explicit reverse lookup. Unknown names are left untouched so this remains
# safe if the dataset is extended with new people.
PERSON_ALIAS_TO_CANONICAL: Dict[str, str] = {
    alias: canonical
    for canonical, aliases in CANONICAL_PERSON_ALIASES.items()
    for alias in aliases
}


def canonical_person_name(name: str) -> str:
    """Return the canonical display name for a person identifier."""
    return PERSON_ALIAS_TO_CANONICAL.get(name, name)


def aliases_for_person(name: str) -> List[str]:
    """Return all source identifiers that belong to the canonical person."""
    canonical = canonical_person_name(name)
    return CANONICAL_PERSON_ALIASES.get(canonical, [canonical])


def canonical_person_names(names: Iterable[str]) -> List[str]:
    """Canonicalize and deduplicate person names while preserving sort order."""
    return sorted({canonical_person_name(name) for name in names if name})


def is_person_alias(name: str) -> bool:
    """Whether a source identifier is an alias rather than a canonical name."""
    return name in PERSON_ALIAS_TO_CANONICAL and name != canonical_person_name(name)
