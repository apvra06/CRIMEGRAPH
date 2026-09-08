import logging
from typing import List, Dict, Any

from app.database import check_connection, run_query
from app.schemas import CaseOverviewStats, LeadershipItem, IntermediaryItem, AnomalyItem
from app.services.mock_data import mock_store

logger = logging.getLogger("crime_analyst.analytics_service")


def get_case_overview() -> CaseOverviewStats:
    if not check_connection():
        mock_store.initialize()
        suspects = sum(1 for n in mock_store.nodes.values() if n["type"] == "Person")
        cells = len({n.get("community") for n in mock_store.nodes.values() if n.get("community") is not None})
        anomalies = len(mock_store.anomalies)

        top_inf = None
        top_score = 0.0
        for n in mock_store.nodes.values():
            if n["type"] == "Person":
                sc = n.get("pageRankScore") or 0.0
                if sc > top_score:
                    top_score = sc
                    top_inf = n["name"]

        return CaseOverviewStats(
            suspects=suspects,
            cells=cells,
            anomalies=anomalies,
            top_influencer=top_inf or "Vikram Malhotra",
            top_influencer_score=round(top_score, 3) if top_score else None,
            is_mock=True
        )

    try:
        stats = run_query("""
            MATCH (p:Person) WITH count(p) AS suspects
            MATCH (x:Person) WHERE x.community IS NOT NULL WITH suspects, count(DISTINCT x.community) AS cells
            MATCH (a) WHERE a.anomalyFlag IS NOT NULL
            RETURN suspects, cells, count(a) AS anomalies
        """)
        top_kingpin = run_query("""
            MATCH (p:Person) RETURN p.name AS name, p.pageRankScore AS score
            ORDER BY score DESC LIMIT 1
        """)

        s = stats[0] if stats else {"suspects": 0, "cells": 0, "anomalies": 0}
        k_name = top_kingpin[0]["name"] if top_kingpin else None
        k_score = top_kingpin[0]["score"] if top_kingpin else None

        return CaseOverviewStats(
            suspects=s.get("suspects", 0),
            cells=s.get("cells", 0),
            anomalies=s.get("anomalies", 0),
            top_influencer=k_name,
            top_influencer_score=round(k_score, 3) if k_score else None,
            is_mock=False
        )
    except Exception as e:
        logger.error("Error fetching case overview: %s. Using mock fallback.", e)
        mock_store.initialize()
        return get_case_overview()


def get_cell_leadership() -> List[LeadershipItem]:
    if not check_connection():
        mock_store.initialize()
        items = []
        persons = [n for n in mock_store.nodes.values() if n["type"] == "Person"]
        sorted_persons = sorted(
            persons,
            key=lambda x: (x.get("community", 0) or 0, -(x.get("pageRankScore", 0) or 0))
        )
        for p in sorted_persons:
            items.append(LeadershipItem(
                person=p["name"],
                community=p.get("community"),
                influence=p.get("pageRankScore")
            ))
        return items

    try:
        rows = run_query("""
            MATCH (p:Person)
            RETURN p.name AS person, p.community AS community, p.pageRankScore AS influence
            ORDER BY community, influence DESC
        """)
        return [LeadershipItem(
            person=r["person"],
            community=r.get("community"),
            influence=round(r["influence"], 4) if r.get("influence") is not None else None
        ) for r in rows]
    except Exception as e:
        logger.error("Error in get_cell_leadership: %s", e)
        mock_store.initialize()
        return get_cell_leadership()


def get_known_intermediaries() -> List[IntermediaryItem]:
    if not check_connection():
        mock_store.initialize()
        persons = [n for n in mock_store.nodes.values() if n["type"] == "Person"]
        sorted_b = sorted(persons, key=lambda x: -(x.get("betweennessScore", 0) or 0))[:10]
        return [IntermediaryItem(
            person=p["name"],
            bridge_score=p.get("betweennessScore")
        ) for p in sorted_b]

    try:
        rows = run_query("""
            MATCH (p:Person)
            RETURN p.name AS person, p.betweennessScore AS bridge_score
            ORDER BY bridge_score DESC LIMIT 10
        """)
        return [IntermediaryItem(
            person=r["person"],
            bridge_score=round(r["bridge_score"], 3) if r.get("bridge_score") is not None else None
        ) for r in rows]
    except Exception as e:
        logger.error("Error in get_known_intermediaries: %s", e)
        mock_store.initialize()
        return get_known_intermediaries()


def get_active_anomalies() -> List[AnomalyItem]:
    if not check_connection():
        mock_store.initialize()
        return [AnomalyItem(
            type=a["type"],
            name=a["name"],
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
            name=r.get("name", "Unknown"),
            flag=r.get("flag", ""),
            calls=r.get("calls"),
            transactions=r.get("transactions")
        ) for r in rows]
    except Exception as e:
        logger.error("Error in get_active_anomalies: %s", e)
        mock_store.initialize()
        return get_active_anomalies()

