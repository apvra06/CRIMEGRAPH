"""
Common intermediate schema every data source normalizes into before it
touches the NLP pipeline or the graph. Keeping one shape here means adding
an 8th source later is "write one loader," not "redesign the pipeline" —
and every node/edge in Neo4j can carry a source_id back to this record for
an audit trail.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    FIR = "FIR"
    CDR = "CDR"
    FINANCIAL = "FINANCIAL"
    SURVEILLANCE = "SURVEILLANCE"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    CRIMINAL_HISTORY = "CRIMINAL_HISTORY"
    INTEL_REPORT = "INTEL_REPORT"


# Sources whose primary content is free text and needs the spaCy pipeline.
NARRATIVE_SOURCES = {SourceType.FIR, SourceType.SURVEILLANCE,
                     SourceType.SOCIAL_MEDIA, SourceType.INTEL_REPORT}

# Sources that are already structured and map straight to graph fields.
STRUCTURED_SOURCES = {SourceType.CDR, SourceType.FINANCIAL, SourceType.CRIMINAL_HISTORY}


@dataclass
class SourceRecord:
    source_type: SourceType
    source_id: str                  # e.g. "SURV-2026-0031"
    timestamp: datetime
    raw_payload: dict                # original fields, kept for audit
    text: str | None = None          # populated for narrative sources -> NLP
    structured_fields: dict | None = None  # populated for structured sources -> direct ETL
    confidence: float = 1.0          # e.g. lower for uncorroborated social media chatter
    metadata: dict = field(default_factory=dict)  # agent_id, classification, handle, etc.

    def to_dict(self):
        d = dict(self.__dict__)
        d["source_type"] = self.source_type.value
        d["timestamp"] = self.timestamp.isoformat()
        return d