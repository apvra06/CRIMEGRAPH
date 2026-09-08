import csv
import json
import logging
from collections import Counter
from typing import Dict, List, Tuple, Any
import networkx as nx

from app.config import DATA_MOCK_DIR, NLP_SERVICE_DIR

logger = logging.getLogger("crime_analyst.mock_data")


class MockGraphStore:
    def __init__(self):
        self._initialized = False
        self.nodes = {}
        self.edges = []
        self.nx_graph = nx.Graph()
        self.role_map = {}
        self.anomalies = []

    def initialize(self):
        if self._initialized:
            return
        try:
            self._load_from_disk()
            self._initialized = True
            logger.info("Loaded mock graph store successfully (%d nodes, %d edges)", len(self.nodes), len(self.edges))
        except Exception as e:
            logger.error("Failed to initialize mock graph store: %s", e)
            self._init_synthetic_fallback()
            self._initialized = True

    def _load_from_disk(self):
        entities_path = NLP_SERVICE_DIR / "extracted_entities.json"
        relationships_path = NLP_SERVICE_DIR / "extracted_relationships.json"
        cdr_path = DATA_MOCK_DIR / "cdr.csv"
        txn_path = DATA_MOCK_DIR / "transactions.csv"

        label_map = {
            "PERSON": "Person",
            "LOCATION": "Location",
            "ORGANIZATION": "Organization",
            "VEHICLE": "Vehicle",
            "PHONE": "PhoneNumber",
        }

        # 1. Load entities
        if entities_path.exists():
            with open(entities_path, "r", encoding="utf-8") as f:
                raw_reports = json.load(f)
                for r in raw_reports:
                    for ent in r.get("entities", []):
                        name = ent.get("text", "").strip()
                        raw_label = ent.get("label", "PERSON")
                        node_type = label_map.get(raw_label, "Person")
                        if name and name not in self.nodes:
                            self.nodes[name] = {
                                "id": name,
                                "name": name,
                                "type": node_type,
                                "community": 0,
                                "pageRankScore": 0.01,
                                "betweennessScore": 0.0,
                                "anomalyFlag": None,
                                "anomalyCallCount": None,
                                "anomalyTxnCount": None,
                            }
                            self.nx_graph.add_node(name, type=node_type)

        # 2. Load relationships
        if relationships_path.exists():
            with open(relationships_path, "r", encoding="utf-8") as f:
                rels = json.load(f)
                for i, r in enumerate(rels):
                    src = r.get("source", "").strip()
                    tgt = r.get("target", "").strip()
                    rel_type = r.get("type", "ASSOCIATED_WITH")
                    date = r.get("date", "2026-03-01")
                    if src and tgt:
                        # Ensure nodes exist
                        if src not in self.nodes:
                            self.nodes[src] = {"id": src, "name": src, "type": "Person", "community": 0}
                            self.nx_graph.add_node(src, type="Person")
                        if tgt not in self.nodes:
                            self.nodes[tgt] = {"id": tgt, "name": tgt, "type": "Person", "community": 0}
                            self.nx_graph.add_node(tgt, type="Person")

                        self.edges.append({
                            "id": f"rel_{i}",
                            "from": src,
                            "to": tgt,
                            "type": rel_type,
                            "date": date,
                            "timestamp": date,
                            "title": f"{rel_type} ({date})"
                        })
                        self.nx_graph.add_edge(src, tgt, type=rel_type, date=date)

        # 3. Detect anomalies from CSVs
        call_flags = {}
        if cdr_path.exists():
            with open(cdr_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                calls = [row["caller_number"] for row in reader if "caller_number" in row]
                counts = Counter(calls)
                if counts:
                    vals = list(counts.values())
                    mean = sum(vals) / len(vals)
                    std = (sum((x - mean) ** 2 for x in vals) / len(vals)) ** 0.5
                    thresh = mean + 2 * std
                    call_flags = {k: v for k, v in counts.items() if v > thresh}

        structuring_flags = {}
        if txn_path.exists():
            with open(txn_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                near_thresh = Counter()
                for row in reader:
                    try:
                        amt = float(row.get("amount", 0))
                        if 45000 <= amt < 50000:
                            near_thresh[row.get("sender_name", "")] += 1
                    except ValueError:
                        pass
                structuring_flags = {k: v for k, v in near_thresh.items() if v >= 2}

        # Apply anomaly flags
        for phone, count in call_flags.items():
            if phone in self.nodes:
                self.nodes[phone]["anomalyFlag"] = f"Call frequency spike ({count} calls)"
                self.nodes[phone]["anomalyCallCount"] = count
                self.anomalies.append({
                    "type": self.nodes[phone]["type"],
                    "name": phone,
                    "flag": f"Call frequency spike ({count} calls)",
                    "calls": count,
                    "transactions": None
                })

        for name, count in structuring_flags.items():
            if name in self.nodes:
                self.nodes[name]["anomalyFlag"] = f"Suspected structuring ({count} sub-threshold transactions)"
                self.nodes[name]["anomalyTxnCount"] = count
                self.anomalies.append({
                    "type": self.nodes[name]["type"],
                    "name": name,
                    "flag": f"Suspected structuring ({count} sub-threshold transactions)",
                    "calls": None,
                    "transactions": count
                })

        # 4. Compute Network Centralities & Communities with NetworkX
        if self.nx_graph.number_of_nodes() > 0:
            try:
                pagerank = nx.pagerank(self.nx_graph)
                betweenness = nx.betweenness_centrality(self.nx_graph)
                communities = list(nx.community.greedy_modularity_communities(self.nx_graph))
            except Exception:
                pagerank = {n: 0.05 for n in self.nx_graph.nodes()}
                betweenness = {n: 0.01 for n in self.nx_graph.nodes()}
                communities = [set(self.nx_graph.nodes())]

            comm_map = {}
            for cid, comm in enumerate(communities):
                for node in comm:
                    comm_map[node] = cid

            for name, ninfo in self.nodes.items():
                ninfo["pageRankScore"] = round(pagerank.get(name, 0.0), 4)
                ninfo["betweennessScore"] = round(betweenness.get(name, 0.0), 3)
                ninfo["community"] = comm_map.get(name, 0)

        # 5. Compute Roles
        self._compute_roles()

    def _init_synthetic_fallback(self):
        # Fallback if mock files missing
        suspects = ["Vikram Malhotra", "Arjun Verma", "Rajesh Sharma", "Karan Singhania", "Tanya Mehra"]
        for s in suspects:
            self.nodes[s] = {
                "id": s, "name": s, "type": "Person", "community": 0,
                "pageRankScore": 0.15, "betweennessScore": 0.08, "anomalyFlag": None
            }
        self.edges = [
            {"id": "e1", "from": suspects[0], "to": suspects[1], "type": "COMMANDS", "date": "2026-03-01", "timestamp": "2026-03-01", "title": "COMMANDS"},
            {"id": "e2", "from": suspects[1], "to": suspects[2], "type": "CALLS", "date": "2026-03-02", "timestamp": "2026-03-02", "title": "CALLS"},
            {"id": "e3", "from": suspects[1], "to": suspects[3], "type": "TRANSFERS_FUNDS", "date": "2026-03-03", "timestamp": "2026-03-03", "title": "TRANSFERS_FUNDS"},
        ]
        self._compute_roles()

    def _compute_roles(self):
        person_nodes = [n for n in self.nodes.values() if n["type"] == "Person"]
        if not person_nodes:
            return

        # Kingpin = highest PageRank in community
        best_in_comm = {}
        for p in person_nodes:
            comm = p.get("community", 0)
            pr = p.get("pageRankScore", 0) or 0
            if comm not in best_in_comm or pr > best_in_comm[comm][1]:
                best_in_comm[comm] = (p["name"], pr)

        kingpins = {name for name, _ in best_in_comm.values()}

        # Intermediary = betweenness >= mean + 1 std
        scores = [p.get("betweennessScore", 0) or 0 for p in person_nodes]
        mean_b = sum(scores) / len(scores) if scores else 0
        variance_b = sum((s - mean_b) ** 2 for s in scores) / len(scores) if scores else 0
        std_b = variance_b ** 0.5
        threshold_b = mean_b + std_b

        for p in person_nodes:
            name = p["name"]
            if name in kingpins:
                self.role_map[name] = "Kingpin"
            elif threshold_b > 0 and (p.get("betweennessScore", 0) or 0) >= threshold_b:
                self.role_map[name] = "Intermediary"
            else:
                self.role_map[name] = "Associate"


mock_store = MockGraphStore()

