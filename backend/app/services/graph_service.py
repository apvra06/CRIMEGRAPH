import logging
import statistics
from typing import Dict, List, Optional, Tuple, Any

from app.database import check_connection, run_query, run_query_raw
from app.schemas import GraphNode, GraphEdge, GraphResponse, NodeStyle, PersonDetail
from app.services.mock_data import mock_store
from app.services.identity import aliases_for_person, canonical_person_name

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
        return {
            canonical_person_name(name): role
            for name, role in mock_store.role_map.items()
        }

    try:
        rows = run_query("""
            MATCH (p:Person)
            RETURN p.name AS name, p.community AS community,
                   p.pageRankScore AS pageRankScore, p.betweennessScore AS betweennessScore
        """)
        if not rows:
            return {}

        # Resolve aliases before determining leadership/intermediary roles.
        canonical_rows = {}
        for r in rows:
            raw_name = r.get("name")
            if not raw_name:
                continue
            canonical = canonical_person_name(raw_name)
            current = canonical_rows.get(canonical)
            if current is None or raw_name == canonical or (
                current.get("name") != canonical
                and (r.get("pageRankScore") or 0) > (current.get("pageRankScore") or 0)
            ):
                canonical_rows[canonical] = {**r, "name": canonical}

        best_in_community = {}
        for r in canonical_rows.values():
            comm = r.get("community")
            pr = r.get("pageRankScore") or 0
            if comm not in best_in_community or pr > best_in_community[comm][1]:
                best_in_community[comm] = (r["name"], pr)
        kingpins = {name for name, _ in best_in_community.values()}

        scores = [r.get("betweennessScore") or 0 for r in canonical_rows.values()]
        mean_b = statistics.mean(scores) if scores else 0
        std_b = statistics.pstdev(scores) if scores else 0
        threshold_b = mean_b + std_b

        roles = {}
        for r in canonical_rows.values():
            if r["name"] in kingpins:
                roles[r["name"]] = "Kingpin"
            elif threshold_b > 0 and (r.get("betweennessScore") or 0) >= threshold_b:
                roles[r["name"]] = "Intermediary"
            else:
                roles[r["name"]] = "Associate"
        return roles
    except Exception as e:
        logger.error("Failed to compute roles from Neo4j: %s. Falling back to mock store.", e)
        mock_store.initialize()
        return {
            canonical_person_name(name): role
            for name, role in mock_store.role_map.items()
        }


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
        person_rows = run_query("""
            MATCH (p:Person)
            RETURN p.name AS name, p.community AS community,
                   p.pageRankScore AS pageRankScore,
                   p.betweennessScore AS betweennessScore,
                   p.anomalyFlag AS anomalyFlag
        """)

        canonical_person_data = {}
        raw_person_names = []
        for row in person_rows:
            raw_name = row.get("name")
            if not raw_name:
                continue
            raw_person_names.append(raw_name)
            canonical = canonical_person_name(raw_name)
            current = canonical_person_data.get(canonical)
            if current is None or raw_name == canonical:
                canonical_person_data[canonical] = row

        params = {}
        where_clauses = []
        if start_date and end_date:
            where_clauses.append(
                "((r.date IS NOT NULL AND left(r.date,10) >= $start AND left(r.date,10) <= $end) "
                "OR (r.timestamp IS NOT NULL AND left(r.timestamp,10) >= $start AND left(r.timestamp,10) <= $end))"
            )
            params["start"], params["end"] = start_date, end_date

        m_label = ":Person" if people_only else ""

        if view_mode == "Specific person":
            canonical_selected = canonical_person_name(selected_person or "")
            selected_names = aliases_for_person(canonical_selected)
            if selected_person and selected_person not in selected_names:
                selected_names.append(selected_person)
            base = f"MATCH (n:Person)-[r]-(m{m_label})"
            where_clauses.insert(0, "n.name IN $selected_names")
            params["selected_names"] = selected_names
        elif view_mode == "Specific community":
            community_names = [
                raw for raw in raw_person_names
                if canonical_person_data.get(canonical_person_name(raw), {}).get("community") == selected_comm
            ]
            base = f"MATCH (n:Person)-[r]-(m{m_label})"
            where_clauses.insert(0, "n.name IN $community_names")
            params["community_names"] = community_names
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
        raw_node_to_display_id = {}

        def flatten(rec):
            for val in rec.values():
                if hasattr(val, "nodes") and hasattr(val, "relationships"):
                    yield from val.nodes
                    yield from val.relationships
                else:
                    yield val

        all_items = [item for rec in records for item in flatten(rec)]

        for item in all_items:
            if not hasattr(item, "labels"):
                continue

            raw_element_id = str(item.element_id)
            node_type = next(iter(item.labels), "Unknown")
            raw_name = item.get("name", "Unknown")

            if node_type == "Person":
                node_name = canonical_person_name(raw_name)
                raw_node_to_display_id[raw_element_id] = node_name
                source_data = canonical_person_data.get(node_name, item)
                role = role_map.get(node_name)
                community = source_data.get("community")
                page_rank = source_data.get("pageRankScore")
                betweenness = source_data.get("betweennessScore")
                anomaly_flag = source_data.get("anomalyFlag")
                node_id = node_name
            else:
                node_id = raw_element_id
                raw_node_to_display_id[raw_element_id] = node_id
                role = None
                community = item.get("community")
                page_rank = item.get("pageRankScore")
                betweenness = item.get("betweennessScore")
                anomaly_flag = item.get("anomalyFlag")
                node_name = raw_name

            if node_id in added_nodes:
                continue

            style = format_node_style(node_type, role, community, anomaly_flag, color_by)
            title_lines = [f"{node_type}: {node_name}"]
            if role:
                title_lines.append(f"Role: {role}")
            if page_rank is not None:
                title_lines.append(f"Influence (PageRank): {page_rank:.3f}")
            if betweenness is not None:
                title_lines.append(f"Bridge score: {betweenness:.2f}")
            if community is not None:
                title_lines.append(f"Cell/Community: {community}")
            if anomaly_flag:
                title_lines.append(f"⚠ FLAGGED: {anomaly_flag}")

            added_nodes[node_id] = GraphNode(
                id=node_id, label=node_name, type=node_type, role=role,
                pageRankScore=page_rank, betweennessScore=betweenness,
                community=community, anomalyFlag=anomaly_flag,
                title="\n".join(title_lines), style=style, level=style.level
            )

        for item in all_items:
            if not (hasattr(item, "type") and hasattr(item, "start_node")):
                continue

            src_id = raw_node_to_display_id.get(str(item.start_node.element_id))
            tgt_id = raw_node_to_display_id.get(str(item.end_node.element_id))
            if not src_id or not tgt_id or src_id not in added_nodes or tgt_id not in added_nodes:
                continue
            if src_id == tgt_id:
                continue

            edge_id = str(item.element_id)
            if edge_id in added_edge_ids:
                continue
            added_edge_ids.add(edge_id)

            date_info = item.get("date") or item.get("timestamp") or ""
            added_edges.append(GraphEdge(
                id=edge_id, from_node=src_id, to_node=tgt_id, type=item.type,
                date=item.get("date"), timestamp=item.get("timestamp"),
                title=f"{item.type} {date_info}".strip(), color="#555555", width=1
            ))

        return GraphResponse(
            nodes=list(added_nodes.values()), edges=added_edges,
            total_nodes=len(added_nodes), total_edges=len(added_edges),
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
    p1_canonical = canonical_person_name(p1)
    p2_canonical = canonical_person_name(p2)
    p1_names = aliases_for_person(p1_canonical)
    p2_names = aliases_for_person(p2_canonical)

    queries = [
        "MATCH path = SHORTEST 1 (a:Person)-[*..6]-(b:Person) "
        "WHERE a.name IN $p1_names AND b.name IN $p2_names RETURN path",
        "MATCH path = shortestPath((a:Person)-[*..6]-(b:Person)) "
        "WHERE a.name IN $p1_names AND b.name IN $p2_names RETURN path",
    ]
    last_error = None
    for q in queries:
        try:
            result = run_query_raw(q, {"p1_names": p1_names, "p2_names": p2_names})
            if result:
                # Format result
                nodes_map = {}
                edges_list = []
                for rec in result:
                    path_obj = rec.get("path")
                    if path_obj:
                        raw_to_display = {}
                        for n in path_obj.nodes:
                            raw_id = str(n.element_id)
                            ntype = next(iter(n.labels), "Person")
                            raw_name = n.get("name", "Unknown")
                            nname = canonical_person_name(raw_name) if ntype == "Person" else raw_name
                            nid = nname if ntype == "Person" else raw_id
                            raw_to_display[raw_id] = nid
                            role = role_map.get(nname) if ntype == "Person" else None
                            community = n.get("community")
                            if ntype == "Person":
                                canonical_detail = run_query("""
                                    MATCH (p:Person {name: $name})
                                    RETURN p.community AS community, p.pageRankScore AS pageRankScore,
                                           p.betweennessScore AS betweennessScore, p.anomalyFlag AS anomalyFlag
                                """, {"name": nname})
                                if canonical_detail:
                                    d = canonical_detail[0]
                                    community = d.get("community")
                                    npr = d.get("pageRankScore")
                                    nbt = d.get("betweennessScore")
                                    naf = d.get("anomalyFlag")
                                else:
                                    npr, nbt, naf = n.get("pageRankScore"), n.get("betweennessScore"), n.get("anomalyFlag")
                            else:
                                npr, nbt, naf = n.get("pageRankScore"), n.get("betweennessScore"), n.get("anomalyFlag")
                            style = format_node_style(ntype, role, community, naf, "Entity type")
                            nodes_map[nid] = GraphNode(
                                id=nid, label=nname, type=ntype, role=role,
                                pageRankScore=npr, betweennessScore=nbt,
                                community=community, anomalyFlag=naf,
                                title=f"{ntype}: {nname}", style=style, level=style.level
                            )
                        for r in path_obj.relationships:
                            src = raw_to_display.get(str(r.start_node.element_id))
                            tgt = raw_to_display.get(str(r.end_node.element_id))
                            if not src or not tgt or src == tgt:
                                continue
                            edges_list.append(GraphEdge(
                                id=str(r.element_id),
                                from_node=src,
                                to_node=tgt,
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
        return sorted({
            canonical_person_name(n["name"])
            for n in mock_store.nodes.values()
            if n["type"] == "Person"
        })

    try:
        people = run_query("MATCH (p:Person) RETURN p.name AS name")
        return sorted({
            canonical_person_name(p["name"])
            for p in people
            if p.get("name")
        })
    except Exception:
        mock_store.initialize()
        return sorted({
            canonical_person_name(n["name"])
            for n in mock_store.nodes.values()
            if n["type"] == "Person"
        })


def get_communities_list() -> List[int]:
    if not check_connection():
        mock_store.initialize()
        comms = {n.get("community") for n in mock_store.nodes.values() if n.get("community") is not None}
        return sorted(list(comms))

    try:
        rows = run_query("MATCH (p:Person) RETURN p.name AS name, p.community AS community")
        canonical_rows = {}
        for r in rows:
            if not r.get("name"):
                continue
            canonical = canonical_person_name(r["name"])
            if canonical not in canonical_rows or r["name"] == canonical:
                canonical_rows[canonical] = r
        return sorted({
            r["community"] for r in canonical_rows.values()
            if r.get("community") is not None
        })
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
        canonical = canonical_person_name(name)
        names = aliases_for_person(canonical)
        detail = run_query("""
            MATCH (p:Person)
            WHERE p.name IN $names
            RETURN p.name AS name, p.pageRankScore AS influence,
                   p.betweennessScore AS bridge_score,
                   p.community AS community, p.anomalyFlag AS flag
        """, {"names": names})
        if not detail:
            return None

        # Prefer the canonical source node for identity-level metrics.
        d = next((row for row in detail if row.get("name") == canonical), detail[0])
        role = role_map.get(canonical, "Associate")

        connections = run_query("""
            MATCH (p:Person)-[r]-(m)
            WHERE p.name IN $names
            RETURN m.name AS entity, labels(m)[0] AS type, type(r) AS relationship
            LIMIT 25
        """, {"names": names})

        # Never expose an alias as a connected Person entity.
        for row in connections:
            if row.get("type") == "Person":
                row["entity"] = canonical_person_name(row.get("entity", ""))

        return PersonDetail(
            name=canonical,
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

