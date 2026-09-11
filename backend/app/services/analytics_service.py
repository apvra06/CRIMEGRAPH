import logging
from typing import List, Dict, Any

from app.database import check_connection, run_query
from app.schemas import CaseOverviewStats, LeadershipItem, IntermediaryItem, AnomalyItem
from app.services.mock_data import mock_store
from app.services.identity import canonical_person_name

logger = logging.getLogger("crime_analyst.analytics_service")


def get_case_overview() -> CaseOverviewStats:
    if not check_connection():
        mock_store.initialize()
        canonical_people = {}
        for n in mock_store.nodes.values():
            if n["type"] != "Person":
                continue
            canonical = canonical_person_name(n["name"])
            current = canonical_people.get(canonical)
            if current is None or n["name"] == canonical:
                canonical_people[canonical] = n

        top = max(
            canonical_people.values(),
            key=lambda n: n.get("pageRankScore", 0) or 0,
            default=None
        )
        communities = {
            n.get("community")
            for n in canonical_people.values()
            if n.get("community") is not None
        }
        return CaseOverviewStats(
            suspects=len(canonical_people),
            cells=len(communities),
            anomalies=len(mock_store.anomalies),
            top_influencer=canonical_person_name(top["name"]) if top else None,
            top_influencer_score=round(top.get("pageRankScore"), 3) if top and top.get("pageRankScore") is not None else None,
            is_mock=True
        )

    try:
        # Count canonical people/cells rather than raw Person nodes.  The source
        # graph intentionally contains aliases as separate source identifiers.
        people = run_query("""
            MATCH (p:Person)
            RETURN p.name AS name, p.community AS community, p.pageRankScore AS score
        """)
        canonical_people = {}
        for row in people:
            raw_name = row.get("name")
            if not raw_name:
                continue
            canonical = canonical_person_name(raw_name)
            current = canonical_people.get(canonical)
            # Prefer the canonical full-name node when it exists; otherwise keep
            # the strongest available source record for that identity.
            if current is None or raw_name == canonical or (current.get("name") != canonical and (row.get("score") or 0) > (current.get("score") or 0)):
                canonical_people[canonical] = row

        anomalies = run_query("""
            MATCH (a) WHERE a.anomalyFlag IS NOT NULL
            RETURN count(a) AS anomalies
        """)
        top_person = max(
            canonical_people.values(),
            key=lambda r: r.get("score") or 0,
            default=None
        )

        communities = {
            row.get("community")
            for row in canonical_people.values()
            if row.get("community") is not None
        }

        return CaseOverviewStats(
            suspects=len(canonical_people),
            cells=len(communities),
            anomalies=(anomalies[0].get("anomalies", 0) if anomalies else 0),
            top_influencer=canonical_person_name(top_person.get("name")) if top_person else None,
            top_influencer_score=round(top_person.get("score"), 3) if top_person and top_person.get("score") is not None else None,
            is_mock=False
        )
    except Exception as e:
        logger.error("Error fetching case overview: %s. Using mock fallback.", e)
        mock_store.initialize()
        return get_case_overview()


def get_cell_leadership() -> List[LeadershipItem]:
    if not check_connection():
        mock_store.initialize()
        canonical_people = {}
        for p in mock_store.nodes.values():
            if p["type"] != "Person":
                continue
            canonical = canonical_person_name(p["name"])
            current = canonical_people.get(canonical)
            if current is None or p["name"] == canonical:
                canonical_people[canonical] = p
        # Rank cell leaders globally by PageRank (highest first).
        sorted_persons = sorted(
            canonical_people.values(),
            key=lambda x: -(x.get("pageRankScore", 0) or 0)
        )
        return [LeadershipItem(
            person=canonical_person_name(p["name"]),
            community=p.get("community"),
            influence=p.get("pageRankScore")
        ) for p in sorted_persons]

    try:
        rows = run_query("""
            MATCH (p:Person)
            RETURN p.name AS person, p.community AS community, p.pageRankScore AS influence
        """)

        # Collapse aliases into their canonical identity. Prefer the canonical
        # node's own community/metrics so aliases cannot create extra cells.
        canonical_rows = {}
        for r in rows:
            raw = r.get("person")
            if not raw:
                continue
            canonical = canonical_person_name(raw)
            current = canonical_rows.get(canonical)
            if current is None or raw == canonical or (
                current.get("person") != canonical
                and (r.get("influence") or 0) > (current.get("influence") or 0)
            ):
                canonical_rows[canonical] = {
                    **r,
                    "person": canonical,
                }

        # Rank cell leaders globally by PageRank (highest first).
        ordered = sorted(
            canonical_rows.values(),
            key=lambda r: -(r.get("influence") or 0)
        )
        return [LeadershipItem(
            person=r["person"],
            community=r.get("community"),
            influence=round(r["influence"], 4) if r.get("influence") is not None else None
        ) for r in ordered]
    except Exception as e:
        logger.error("Error in get_cell_leadership: %s", e)
        mock_store.initialize()
        return get_cell_leadership()


def get_known_intermediaries() -> List[IntermediaryItem]:
    if not check_connection():
        mock_store.initialize()
        canonical_people = {}
        for p in mock_store.nodes.values():
            if p["type"] != "Person":
                continue
            canonical = canonical_person_name(p["name"])
            current = canonical_people.get(canonical)
            if current is None or p["name"] == canonical or (p.get("betweennessScore", 0) or 0) > (current.get("betweennessScore", 0) or 0):
                canonical_people[canonical] = p
        sorted_b = sorted(
            canonical_people.values(),
            key=lambda x: -(x.get("betweennessScore", 0) or 0)
        )[:10]
        return [IntermediaryItem(
            person=canonical_person_name(p["name"]),
            bridge_score=p.get("betweennessScore")
        ) for p in sorted_b]

    try:
        rows = run_query("""
            MATCH (p:Person)
            RETURN p.name AS person, p.betweennessScore AS bridge_score
        """)
        # Keep one intermediary row per canonical identity.
        canonical_rows = {}
        for r in rows:
            raw = r.get("person")
            if not raw:
                continue
            canonical = canonical_person_name(raw)
            score = r.get("bridge_score") or 0
            current = canonical_rows.get(canonical)
            if current is None or score > (current.get("bridge_score") or 0) or raw == canonical:
                canonical_rows[canonical] = {
                    **r,
                    "person": canonical,
                }

        ordered = sorted(
            canonical_rows.values(),
            key=lambda r: -(r.get("bridge_score") or 0)
        )[:10]
        return [IntermediaryItem(
            person=r["person"],
            bridge_score=round(r["bridge_score"], 3) if r.get("bridge_score") is not None else None
        ) for r in ordered]
    except Exception as e:
        logger.error("Error in get_known_intermediaries: %s", e)
        mock_store.initialize()
        return get_known_intermediaries()


def get_active_anomalies() -> List[AnomalyItem]:
    if not check_connection():
        mock_store.initialize()
        return [AnomalyItem(
            type=a["type"],
            name=canonical_person_name(a["name"]) if a.get("type") == "Person" else a["name"],
            flag=a["flag"],
            calls=a.get("calls"),
            transactions=a.get("transactions")
        ) for a in mock_store.anomalies]

    try:
        rows = run_query("""
            MATCH (n) WHERE n.anomalyFlag IS NOT NULL
            RETURN labels(n)[0] AS type, n.name AS name, n.anomalyFlag AS flag,
                   n.anomalyCallCount AS calls, n.anomalyTxnCount AS transactions
        """)
        return [AnomalyItem(
            type=r.get("type", "Unknown"),
            name=canonical_person_name(r.get("name", "Unknown")) if r.get("type") == "Person" else r.get("name", "Unknown"),
            flag=r.get("flag", ""),
            calls=r.get("calls"),
            transactions=r.get("transactions")
        ) for r in rows]
    except Exception as e:
        logger.error("Error in get_active_anomalies: %s", e)
        mock_store.initialize()
        return get_active_anomalies()

