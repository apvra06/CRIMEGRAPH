import logging
import statistics
from typing import Dict, List, Optional, Tuple, Any

from app.database import check_connection, run_query, run_query_raw
from app.schemas import GraphNode, GraphEdge, GraphResponse, NodeStyle, PersonDetail
from app.services.mock_data import mock_store

logger = logging.getLogger("crime_analyst.graph_service")

# Design Tokens (matching dashboard/app.py)
BG = "#0B0F1A"
SURFACE = "#131826"
BORDER = "#232A3D"
AMBER = "#C99A3C"
TEAL = "#4FB6AC"
ALERT = "#D9480F"
TEXT_MUTED = "#8A93A6"

ROLE_STYLE = {
    "Kingpin":      {"shape": "star",         "color": "#E5B94E", "size": 46, "borderWidth": 3, "glyph": "★"},
    "Intermediary": {"shape": "diamond",      "color": TEAL,      "size": 34, "borderWidth": 3, "glyph": "◆"},
    "Associate":    {"shape": "dot",          "color": "#6B93C9", "size": 20, "borderWidth": 1, "glyph": "●"},
}
ROLE_LEVEL = {"Kingpin": 0, "Intermediary": 1, "Associate": 2}

TYPE_STYLE = {
    "Location":     {"shape": "square",       "color": "#5E8FC9", "glyph": "■"},
    "Organization": {"shape": "triangle",     "color": "#8C7BC9", "glyph": "▲"},
    "PhoneNumber":  {"shape": "triangleDown", "color": "#9CC97B", "glyph": "▼"},
    "Vehicle":      {"shape": "box",          "color": "#C97B9C", "glyph": "▢"},
}

COMMUNITY_PALETTE = ["#C99A3C", "#4FB6AC", "#8C7BC9", "#9CC97B", "#C97B9C", "#6B93C9", "#C9A05E", "#5EC9AE"]
ANOMALY_COLOR = ALERT


def compute_roles() -> Dict[str, str]:
    if not check_connection():
        mock_store.initialize()
        return mock_store.role_map

    try:
        rows = run_query("""
            MATCH (p:Person)
            RETURN p.name AS name, p.community AS community,
                   p.pageRankScore AS pageRankScore, p.betweennessScore AS betweennessScore
        """)
        if not rows:
            return {}

        best_in_community = {}
        for r in rows:
            comm = r["community"]
            pr = r["pageRankScore"] or 0
            if comm not in best_in_community or pr > best_in_community[comm][1]:
                best_in_community[comm] = (r["name"], pr)
        kingpins = {name for name, _ in best_in_community.values()}

        scores = [r["betweennessScore"] or 0 for r in rows]
        mean_b = statistics.mean(scores) if scores else 0
        std_b = statistics.pstdev(scores) if scores else 0
        threshold_b = mean_b + std_b

        roles = {}
        for r in rows:
            if r["name"] in kingpins:
                roles[r["name"]] = "Kingpin"
            elif threshold_b > 0 and (r["betweennessScore"] or 0) >= threshold_b:
                roles[r["name"]] = "Intermediary"
            else:
                roles[r["name"]] = "Associate"
        return roles
    except Exception as e:
        logger.error("Failed to compute roles from Neo4j: %s. Falling back to mock store.", e)
        mock_store.initialize()
        return mock_store.role_map


def format_node_style(node_type: str, role: Optional[str], community: Optional[int], anomaly_flag: Optional[str], color_by: str) -> NodeStyle:
    if node_type == "Person":
        r = role or "Associate"
        s = dict(ROLE_STYLE.get(r, ROLE_STYLE["Associate"]))
        if color_by == "Community" and community is not None:
            s["color"] = COMMUNITY_PALETTE[community % len(COMMUNITY_PALETTE)]
        if anomaly_flag:
            s["color"] = ANOMALY_COLOR
        lvl = ROLE_LEVEL.get(r, 2)
        return NodeStyle(
            shape=s["shape"],
            color=s["color"],
            size=s["size"],
            borderWidth=s.get("borderWidth", 1),
            glyph=s.get("glyph", "●"),
            level=lvl
        )
    else:
        s = dict(TYPE_STYLE.get(node_type, {"shape": "dot", "color": "#999999", "glyph": "●"}))
        size = 16
        border_width = 1
        color = s["color"]
        if anomaly_flag:
            color = ANOMALY_COLOR
        return NodeStyle(
            shape=s["shape"],
            color=color,
            size=size,
            borderWidth=border_width,
            glyph=s.get("glyph", "●"),
            level=3
        )


def get_graph_data(
    view_mode: str = "Whole network",
    selected_person: Optional[str] = None,
    selected_comm: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    people_only: bool = False,
    color_by: str = "Entity type"
) -> GraphResponse:
    role_map = compute_roles()

    if not check_connection():
        # Fallback to mock store
        mock_store.initialize()
        return _get_mock_graph_data(
            role_map=role_map,
            view_mode=view_mode,
            selected_person=selected_person,
            selected_comm=selected_comm,
            start_date=start_date,
            end_date=end_date,
            people_only=people_only,
            color_by=color_by
        )

    try:
        where_clauses = []
        params = {}
        if start_date and end_date:
            where_clauses.append(
                "((r.date IS NOT NULL AND left(r.date,10) >= $start AND left(r.date,10) <= $end) "
                "OR (r.timestamp IS NOT NULL AND left(r.timestamp,10) >= $start AND left(r.timestamp,10) <= $end))"
            )
            params["start"], params["end"] = start_date, end_date

        m_label = ":Person" if people_only else ""
        if view_mode == "Specific person":
            base = f"MATCH (n:Person {{name: $name}})-[r]-(m{m_label})"
            params["name"] = selected_person
        elif view_mode == "Specific community":
            base = f"MATCH (n:Person {{community: $comm}})-[r]-(m{m_label})"
            params["comm"] = selected_comm
        else:
            n_label = ":Person" if people_only else ""
            base = f"MATCH (n{n_label})-[r]-(m{m_label})"

        query = base
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " RETURN n, r, m LIMIT 300"

        records = run_query_raw(query, params)

        added_nodes = {}
        added_edges = []
        added_edge_ids = set()

        def flatten(rec):
            for val in rec.values():
                if hasattr(val, "nodes") and hasattr(val, "relationships"):
                    yield from val.nodes
                    yield from val.relationships
                else:
                    yield val

        all_items = [item for rec in records for item in flatten(rec)]

        for item in all_items:
            if hasattr(item, "labels"):
                node_id = str(item.element_id)
                if node_id in added_nodes:
                    continue
                node_name = item.get("name", "Unknown")
                node_type = next(iter(item.labels), "Unknown")
                role = role_map.get(node_name) if node_type == "Person" else None
                community = item.get("community")
                anomaly_flag = item.get("anomalyFlag")

                style = format_node_style(node_type, role, community, anomaly_flag, color_by)

                title_lines = [f"{node_type}: {node_name}"]
                if role:
                    title_lines.append(f"Role: {role}")
                if item.get("pageRankScore") is not None:
                    title_lines.append(f"Influence (PageRank): {item.get('pageRankScore'):.3f}")
                if item.get("betweennessScore") is not None:
                    title_lines.append(f"Bridge score: {item.get('betweennessScore'):.2f}")
                if community is not None:
                    title_lines.append(f"Cell/Community: {community}")
                if anomaly_flag:
                    title_lines.append(f"⚠ FLAGGED: {anomaly_flag}")

                added_nodes[node_id] = GraphNode(
                    id=node_id,
                    label=node_name,
                    type=node_type,
                    role=role,
                    pageRankScore=item.get("pageRankScore"),
                    betweennessScore=item.get("betweennessScore"),
                    community=community,
                    anomalyFlag=anomaly_flag,
                    title="\n".join(title_lines),
                    style=style,
                    level=style.level
                )

        for item in all_items:
            if hasattr(item, "type") and hasattr(item, "start_node"):
                src_id = str(item.start_node.element_id)
                tgt_id = str(item.end_node.element_id)
                if src_id in added_nodes and tgt_id in added_nodes:
                    edge_id = str(item.element_id)

                    # Neo4j undirected MATCH can return the same relationship
                    # from both directions. Keep each relationship only once.
                    if edge_id in added_edge_ids:
                        continue

                    added_edge_ids.add(edge_id)

                    date_info = item.get("date") or item.get("timestamp") or ""
                    added_edges.append(GraphEdge(
                        id=edge_id,
                        from_node=src_id,
                        to_node=tgt_id,
                        type=item.type,
                        date=item.get("date"),
                        timestamp=item.get("timestamp"),
                        title=f"{item.type} {date_info}".strip(),
                        color="#555555",
                        width=1
                    ))

        return GraphResponse(
            nodes=list(added_nodes.values()),
            edges=added_edges,
            total_nodes=len(added_nodes),
            total_edges=len(added_edges),
            is_mock=False
        )

    except Exception as e:
        logger.error("Error executing Cypher query in get_graph_data: %s. Using mock fallback.", e)
        mock_store.initialize()
        return _get_mock_graph_data(
            role_map=role_map,
            view_mode=view_mode,
            selected_person=selected_person,
            selected_comm=selected_comm,
            start_date=start_date,
            end_date=end_date,
            people_only=people_only,
            color_by=color_by
        )


def _get_mock_graph_data(
    role_map: Dict[str, str],
    view_mode: str,
    selected_person: Optional[str],
    selected_comm: Optional[int],
    start_date: Optional[str],
    end_date: Optional[str],
    people_only: bool,
    color_by: str
) -> GraphResponse:
    matched_nodes = {}
    matched_edges = []

    nodes_dict = mock_store.nodes
    edges_list = mock_store.edges

    # Determine which nodes match view_mode
    if view_mode == "Specific person" and selected_person:
        direct_neighbors = {selected_person}
        for e in edges_list:
            if e["from"] == selected_person:
                direct_neighbors.add(e["to"])
            elif e["to"] == selected_person:
                direct_neighbors.add(e["from"])
        candidate_node_ids = direct_neighbors
    elif view_mode == "Specific community" and selected_comm is not None:
        candidate_node_ids = {
            nid for nid, n in nodes_dict.items()
            if n.get("community") == selected_comm
        }
    else:
        candidate_node_ids = set(nodes_dict.keys())

    for nid in candidate_node_ids:
        n = nodes_dict.get(nid)
        if not n:
            continue
        if people_only and n["type"] != "Person":
            continue

        role = role_map.get(n["name"]) if n["type"] == "Person" else None
        style = format_node_style(n["type"], role, n.get("community"), n.get("anomalyFlag"), color_by)

        title_lines = [f"{n['type']}: {n['name']}"]
        if role:
            title_lines.append(f"Role: {role}")
        if n.get("pageRankScore") is not None:
            title_lines.append(f"Influence (PageRank): {n['pageRankScore']:.3f}")
        if n.get("betweennessScore") is not None:
            title_lines.append(f"Bridge score: {n['betweennessScore']:.2f}")
        if n.get("community") is not None:
            title_lines.append(f"Cell/Community: {n['community']}")
        if n.get("anomalyFlag"):
            title_lines.append(f"⚠ FLAGGED: {n['anomalyFlag']}")

        matched_nodes[nid] = GraphNode(
            id=nid,
            label=n["name"],
            type=n["type"],
            role=role,
            pageRankScore=n.get("pageRankScore"),
            betweennessScore=n.get("betweennessScore"),
            community=n.get("community"),
            anomalyFlag=n.get("anomalyFlag"),
            title="\n".join(title_lines),
            style=style,
            level=style.level
        )

    for e in edges_list:
        src = e["from"]
        tgt = e["to"]
        if src in matched_nodes and tgt in matched_nodes:
            date_val = e.get("date") or e.get("timestamp") or ""
            if start_date and end_date and date_val:
                d = date_val[:10]
                if not (start_date <= d <= end_date):
                    continue
            matched_edges.append(GraphEdge(
                id=e["id"],
                from_node=src,
                to_node=tgt,
                type=e["type"],
                date=e.get("date"),
                timestamp=e.get("timestamp"),
                title=f"{e['type']} {date_val}".strip(),
                color="#555555",
                width=1
            ))

    return GraphResponse(
        nodes=list(matched_nodes.values()),
        edges=matched_edges,
        total_nodes=len(matched_nodes),
        total_edges=len(matched_edges),
        is_mock=True
    )


def find_shortest_path(p1: str, p2: str) -> Tuple[List[GraphNode], List[GraphEdge], Optional[str]]:
    role_map = compute_roles()

    if not check_connection():
        mock_store.initialize()
        import networkx as nx
        try:
            path = nx.shortest_path(mock_store.nx_graph, source=p1, target=p2)
            nodes = []
            edges = []
            for i, name in enumerate(path):
                n = mock_store.nodes.get(name, {"name": name, "type": "Person"})
                role = role_map.get(name) if n["type"] == "Person" else None
                style = format_node_style(n["type"], role, n.get("community"), n.get("anomalyFlag"), "Entity type")
                nodes.append(GraphNode(
                    id=name,
                    label=name,
                    type=n["type"],
                    role=role,
                    pageRankScore=n.get("pageRankScore"),
                    betweennessScore=n.get("betweennessScore"),
                    community=n.get("community"),
                    anomalyFlag=n.get("anomalyFlag"),
                    title=f"{n['type']}: {name}\nRole: {role or 'Associate'}",
                    style=style,
                    level=style.level
                ))
                if i < len(path) - 1:
                    nxt = path[i + 1]
                    edges.append(GraphEdge(
                        id=f"p_{name}_{nxt}",
                        from_node=name,
                        to_node=nxt,
                        type="CONNECTED_TO",
                        title=f"{name} -> {nxt}",
                        color="#C99A3C",
                        width=2
                    ))
            return nodes, edges, None
        except Exception as e:
            return [], [], f"No path found: {e}"

    # Using Neo4j
    queries = [
        "MATCH path = SHORTEST 1 (a:Person {name: $p1})-[*..6]-(b:Person {name: $p2}) RETURN path",
        "MATCH path = shortestPath((a:Person {name: $p1})-[*..6]-(b:Person {name: $p2})) RETURN path",
    ]
    last_error = None
    for q in queries:
        try:
            result = run_query_raw(q, {"p1": p1, "p2": p2})
            if result:
                # Format result
                nodes_map = {}
                edges_list = []
                for rec in result:
                    path_obj = rec.get("path")
                    if path_obj:
                        for n in path_obj.nodes:
                            nid = str(n.element_id)
                            nname = n.get("name", "Unknown")
                            ntype = next(iter(n.labels), "Person")
                            role = role_map.get(nname) if ntype == "Person" else None
                            style = format_node_style(ntype, role, n.get("community"), n.get("anomalyFlag"), "Entity type")
                            nodes_map[nid] = GraphNode(
                                id=nid,
                                label=nname,
                                type=ntype,
                                role=role,
                                pageRankScore=n.get("pageRankScore"),
                                betweennessScore=n.get("betweennessScore"),
                                community=n.get("community"),
                                anomalyFlag=n.get("anomalyFlag"),
                                title=f"{ntype}: {nname}",
                                style=style,
                                level=style.level
                            )
                        for r in path_obj.relationships:
                            edges_list.append(GraphEdge(
                                id=str(r.element_id),
                                from_node=str(r.start_node.element_id),
                                to_node=str(r.end_node.element_id),
                                type=r.type,
                                title=r.type,
                                color="#C99A3C",
                                width=2
                            ))
                return list(nodes_map.values()), edges_list, None
        except Exception as e:
            last_error = str(e)
            continue

    return [], [], last_error or "No connection path found between these two individuals."


def get_people_names() -> List[str]:
    if not check_connection():
        mock_store.initialize()
        return sorted([n["name"] for n in mock_store.nodes.values() if n["type"] == "Person"])

    try:
        people = run_query("MATCH (p:Person) RETURN p.name AS name ORDER BY name")
        return [p["name"] for p in people if p.get("name")]
    except Exception:
        mock_store.initialize()
        return sorted([n["name"] for n in mock_store.nodes.values() if n["type"] == "Person"])


def get_communities_list() -> List[int]:
    if not check_connection():
        mock_store.initialize()
        comms = {n.get("community") for n in mock_store.nodes.values() if n.get("community") is not None}
        return sorted(list(comms))

    try:
        res = run_query("MATCH (p:Person) RETURN DISTINCT p.community AS community ORDER BY community")
        return [r["community"] for r in res if r.get("community") is not None]
    except Exception:
        mock_store.initialize()
        comms = {n.get("community") for n in mock_store.nodes.values() if n.get("community") is not None}
        return sorted(list(comms))


def get_date_range() -> Tuple[Optional[str], Optional[str]]:
    if not check_connection():
        mock_store.initialize()
        dates = []
        for e in mock_store.edges:
            d = e.get("date") or e.get("timestamp")
            if d:
                dates.append(d[:10])
        dates = sorted(set(dates))
        if dates:
            return dates[0], dates[-1]
        return None, None

    try:
        rows = run_query("""
            MATCH ()-[r]->() WHERE r.date IS NOT NULL RETURN left(r.date,10) AS d
            UNION MATCH ()-[r]->() WHERE r.timestamp IS NOT NULL RETURN left(r.timestamp,10) AS d
        """)
        dates = sorted(set(row["d"] for row in rows if row.get("d")))
        if dates:
            return dates[0], dates[-1]
        return None, None
    except Exception:
        mock_store.initialize()
        dates = []
        for e in mock_store.edges:
            d = e.get("date") or e.get("timestamp")
            if d:
                dates.append(d[:10])
        dates = sorted(set(dates))
        if dates:
            return dates[0], dates[-1]
        return None, None


def get_person_detail(name: str) -> Optional[PersonDetail]:
    role_map = compute_roles()

    if not check_connection():
        mock_store.initialize()
        n = mock_store.nodes.get(name)
        if not n:
            return None
        role = role_map.get(name, "Associate")
        connected = []
        for e in mock_store.edges:
            if e["from"] == name:
                connected.append({"entity": e["to"], "relationship": e["type"], "direction": "outgoing"})
            elif e["to"] == name:
                connected.append({"entity": e["from"], "relationship": e["type"], "direction": "incoming"})

        return PersonDetail(
            name=name,
            role=role,
            influence=n.get("pageRankScore"),
            bridge_score=n.get("betweennessScore"),
            community=n.get("community"),
            flag=n.get("anomalyFlag"),
            connections_count=len(connected),
            connected_entities=connected[:20]
        )

    try:
        detail = run_query("""
            MATCH (p:Person {name: $name})
            RETURN p.pageRankScore AS influence, p.betweennessScore AS bridge_score,
                   p.community AS community, p.anomalyFlag AS flag
        """, {"name": name})
        if not detail:
            return None
        d = detail[0]
        role = role_map.get(name, "Associate")

        connections = run_query("""
            MATCH (p:Person {name: $name})-[r]-(m)
            RETURN m.name AS entity, labels(m)[0] AS type, type(r) AS relationship
            LIMIT 25
        """, {"name": name})

        return PersonDetail(
            name=name,
            role=role,
            influence=d.get("influence"),
            bridge_score=d.get("bridge_score"),
            community=d.get("community"),
            flag=d.get("flag"),
            connections_count=len(connections),
            connected_entities=connections
        )
    except Exception as e:
        logger.error("Error retrieving person detail for %s: %s", name, e)
        mock_store.initialize()
        n = mock_store.nodes.get(name)
        if not n:
            return None
        return PersonDetail(
            name=name,
            role=role_map.get(name, "Associate"),
            influence=n.get("pageRankScore"),
            bridge_score=n.get("betweennessScore"),
            community=n.get("community"),
            flag=n.get("anomalyFlag")
        )

