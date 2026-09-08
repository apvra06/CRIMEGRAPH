"""
Streamlit dashboard for the AI-powered criminal network analysis prototype.

Run with: streamlit run app.py
Requires config.py (copy config_template.py and fill in real credentials).
"""
import statistics
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from neo4j import GraphDatabase
from pyvis.network import Network
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

st.set_page_config(page_title="Crime Network Analysis", layout="wide", page_icon="◆")

# --------------------------------------------------------- Design tokens ---
BG = "#0B0F1A"
SURFACE = "#131826"
BORDER = "#232A3D"
AMBER = "#C99A3C"
TEAL = "#4FB6AC"
ALERT = "#D9480F"
TEXT_MUTED = "#8A93A6"

# Role styling for Person nodes — shape carries the primary signal (so it
# reads correctly even in grayscale/print), color reinforces it.
ROLE_STYLE = {
    "Kingpin":      {"shape": "star",     "color": "#E5B94E", "size": 46, "borderWidth": 3, "glyph": "★"},
    "Intermediary": {"shape": "diamond",  "color": TEAL,      "size": 34, "borderWidth": 3, "glyph": "◆"},
    "Associate":    {"shape": "dot",      "color": "#6B93C9", "size": 20, "borderWidth": 1, "glyph": "●"},
}
ROLE_LEVEL = {"Kingpin": 0, "Intermediary": 1, "Associate": 2}

# Non-person entity types get their own shape+color, distinct from any role
TYPE_STYLE = {
    "Location":     {"shape": "square",      "color": "#5E8FC9", "glyph": "■"},
    "Organization": {"shape": "triangle",    "color": "#8C7BC9", "glyph": "▲"},
    "PhoneNumber":  {"shape": "triangleDown", "color": "#9CC97B", "glyph": "▼"},
    "Vehicle":      {"shape": "box",         "color": "#C97B9C", "glyph": "▢"},
}

COMMUNITY_PALETTE = ["#C99A3C", "#4FB6AC", "#8C7BC9", "#9CC97B", "#C97B9C", "#6B93C9", "#C9A05E", "#5EC9AE"]
ANOMALY_COLOR = ALERT

# --------------------------------------------------------------- Styling ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    html, body, [class*="css"], p, span, div {{ font-family: 'IBM Plex Sans', sans-serif; }}
    h1, h2, h3, h4, .stTabs [data-baseweb="tab"], label, code,
    div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {{
        font-family: 'IBM Plex Mono', monospace !important;
    }}

    .stApp {{ background-color: {BG}; }}

    .hero {{
        padding: 1.1rem 1.4rem; margin-bottom: 1.2rem;
        background-color: {SURFACE};
        border-left: 3px solid {AMBER};
        border-top: 1px solid {BORDER}; border-right: 1px solid {BORDER}; border-bottom: 1px solid {BORDER};
    }}
    .hero h1 {{ margin: 0; font-size: 1.5rem; font-weight: 600; letter-spacing: 0.02em; }}
    .hero p {{ margin: 0.3rem 0 0 0; color: {TEXT_MUTED}; font-size: 0.85rem; }}
    .case-id {{ color: {TEAL}; }}

    div[data-testid="stMetric"] {{
        background-color: {SURFACE}; border: 1px solid {BORDER};
        border-left: 2px solid {AMBER}; border-radius: 2px; padding: 0.7rem 0.9rem;
    }}
    div[data-testid="stMetricValue"] {{ font-size: 1.3rem; }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {BORDER}; }}
    .stTabs [aria-selected="true"] {{ color: {AMBER} !important; border-bottom-color: {AMBER} !important; }}

    .legend-item {{ display: inline-block; margin-right: 16px; font-size: 0.8rem; color: {TEXT_MUTED}; font-family: 'IBM Plex Mono', monospace; }}
    .legend-glyph {{ margin-right: 5px; }}

    section[data-testid="stSidebar"] {{ background-color: {SURFACE}; border-right: 1px solid {BORDER}; }}
    div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; }}
</style>
""", unsafe_allow_html=True)


def show_table(df):
    if df is not None and not df.empty:
        df = df.copy()
        df.index = range(1, len(df) + 1)
    st.dataframe(df, use_container_width=True)


@st.cache_resource
def get_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    return driver


def run_query(query, params=None):
    with get_driver().session() as session:
        return [record.data() for record in session.run(query, params or {})]


def run_query_raw(query, params=None):
    with get_driver().session() as session:
        return list(session.run(query, params or {}))


def find_shortest_path(p1, p2):
    """Tries the modern Cypher 25 'SHORTEST' path-selector syntax first,
    then falls back to the legacy shortestPath() function — Neo4j is
    transitioning between the two, so which one works depends on the exact
    server version. Both return a record under the key 'path'."""
    queries = [
        "MATCH path = SHORTEST 1 (a:Person {name: $p1})-[*..6]-(b:Person {name: $p2}) RETURN path",
        "MATCH path = shortestPath((a:Person {name: $p1})-[*..6]-(b:Person {name: $p2})) RETURN path",
    ]
    last_error = None
    for q in queries:
        try:
            result = run_query_raw(q, {"p1": p1, "p2": p2})
            if result:
                return result, None
        except Exception as e:
            last_error = e
            continue
    return [], last_error


@st.cache_data(ttl=30)
def compute_roles():
    """Classifies every Person into Kingpin / Intermediary / Associate:
      - Kingpin: highest PageRank WITHIN their own detected community
        (so each cell gets its own leader, not just one global winner)
      - Intermediary: betweenness centrality notably above the network
        average (mean + 1 std), i.e. a real structural bridge
      - Associate: everyone else
    """
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
    mean_b = statistics.mean(scores)
    std_b = statistics.pstdev(scores)
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


def build_graph_query(view_mode, selected_person=None, selected_comm=None, date_range=None, people_only=False):
    where_clauses = []
    params = {}
    if date_range:
        where_clauses.append(
            "((r.date IS NOT NULL AND left(r.date,10) >= $start AND left(r.date,10) <= $end) "
            "OR (r.timestamp IS NOT NULL AND left(r.timestamp,10) >= $start AND left(r.timestamp,10) <= $end))"
        )
        params["start"], params["end"] = date_range

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
    return query, params


def node_style(node, role_map, color_by):
    node_type = next(iter(node.labels), "Unknown")
    if node_type == "Person":
        role = role_map.get(node.get("name"), "Associate")
        style = dict(ROLE_STYLE[role])
        if color_by == "Community" and node.get("community") is not None:
            style["color"] = COMMUNITY_PALETTE[node.get("community") % len(COMMUNITY_PALETTE)]
        if node.get("anomalyFlag"):
            style["color"] = ANOMALY_COLOR
        style["level"] = ROLE_LEVEL[role]
        return style, role
    else:
        style = dict(TYPE_STYLE.get(node_type, {"shape": "dot", "color": "#999999", "glyph": "●"}))
        style.setdefault("size", 16)
        style.setdefault("borderWidth", 1)
        if node.get("anomalyFlag"):
            style["color"] = ANOMALY_COLOR
        style["level"] = 3
        return style, None


def render_graph(records, role_map, color_by="Entity type", layout="Force-directed", height=650):
    net = Network(height=f"{height}px", width="100%", bgcolor="#0E1117", font_color="#EEEEEE", directed=False)
    added_nodes = set()

    def flatten(record):
        for value in record.values():
            if hasattr(value, "nodes") and hasattr(value, "relationships"):  # Path
                yield from value.nodes
                yield from value.relationships
            else:
                yield value

    all_items = [item for record in records for item in flatten(record)]

    for item in all_items:
        if hasattr(item, "labels"):  # Node
            node_id = item.element_id
            if node_id in added_nodes:
                continue
            label = item.get("name", "Unknown")
            node_type = next(iter(item.labels), "Unknown")
            style, role = node_style(item, role_map, color_by)

            title_lines = [f"{node_type}: {label}"]
            if role:
                title_lines.append(f"Role: {role}")
            if item.get("pageRankScore") is not None:
                title_lines.append(f"Influence (PageRank): {item.get('pageRankScore'):.3f}")
            if item.get("betweennessScore") is not None:
                title_lines.append(f"Bridge score: {item.get('betweennessScore'):.2f}")
            if item.get("community") is not None:
                title_lines.append(f"Cell/Community: {item.get('community')}")
            if item.get("anomalyFlag"):
                title_lines.append(f"⚠ FLAGGED: {item.get('anomalyFlag')}")

            net.add_node(node_id, label=label, title="\n".join(title_lines),
                         shape=style["shape"], color=style["color"],
                         size=style["size"], borderWidth=style["borderWidth"],
                         level=style["level"])
            added_nodes.add(node_id)

    for item in all_items:
        if hasattr(item, "type") and hasattr(item, "start_node"):  # Relationship
            if item.start_node.element_id in added_nodes and item.end_node.element_id in added_nodes:
                date_info = item.get("date") or item.get("timestamp") or ""
                net.add_edge(item.start_node.element_id, item.end_node.element_id,
                             title=f"{item.type}  {date_info}", color="#555555", width=1)

    if layout == "Hierarchical (by role)":
        options = """
        {
          "nodes": {"font": {"size": 14}},
          "layout": {"hierarchical": {"enabled": true, "direction": "UD",
                     "sortMethod": "directed", "levelSeparation": 160, "nodeSpacing": 140}},
          "physics": {"hierarchicalRepulsion": {"nodeDistance": 140}, "solver": "hierarchicalRepulsion",
                      "stabilization": {"enabled": true, "iterations": 250}},
          "interaction": {"hover": true, "navigationButtons": true, "keyboard": true}
        }
        """
    else:
        net.barnes_hut(gravity=-4000, central_gravity=0.35, spring_length=110, spring_strength=0.045, damping=0.15)
        options = """
        {
          "nodes": {"font": {"size": 14}},
          "physics": {"stabilization": {"enabled": true, "iterations": 250}},
          "interaction": {"hover": true, "navigationButtons": true, "keyboard": true}
        }
        """
    net.set_options(options)

    net.save_graph("_graph.html")
    with open("_graph.html", "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace(
        "</body>",
        "<script>network.once('stabilizationIterationsDone', function() { network.fit({animation:true}); });</script></body>"
    )
    components.html(html, height=height + 20)


def render_legend(color_by):
    parts = []
    for role, style in ROLE_STYLE.items():
        parts.append(f'<span class="legend-item"><span class="legend-glyph" style="color:{style["color"]}">{style["glyph"]}</span>{role}</span>')
    if color_by == "Entity type":
        for etype, style in TYPE_STYLE.items():
            parts.append(f'<span class="legend-item"><span class="legend-glyph" style="color:{style["color"]}">{style["glyph"]}</span>{etype}</span>')
    else:
        for i, c in enumerate(COMMUNITY_PALETTE[:4]):
            parts.append(f'<span class="legend-item"><span class="legend-glyph" style="color:{c}">●</span>Community {i}</span>')
    parts.append(f'<span class="legend-item"><span class="legend-glyph" style="color:{ANOMALY_COLOR}">⚠</span>Flagged anomaly</span>')
    st.markdown("".join(parts), unsafe_allow_html=True)


# ------------------------------------------------------------------ Hero ---
st.markdown("""
<div class="hero">
  <h1>AI-Powered Criminal Network Analysis</h1>
  <p>Case <span class="case-id">NCRB-2026-0847</span> — fused FIR, CDR &amp; financial transaction intelligence</p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------- Sidebar ---
with st.sidebar:
    st.markdown("#### Case File")
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
    if stats:
        s = stats[0]
        st.metric("Total Suspects", s["suspects"])
        st.metric("Cells Detected", s["cells"])
        st.metric("Anomalies Flagged", s["anomalies"])
    if top_kingpin:
        st.metric("Top Influencer", top_kingpin[0]["name"])
    st.divider()
    st.caption("Sources: FIR reports, CDR, financial transactions (synthetic/mock)")

# -------------------------------------------------------------------- UI ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["Network Explorer", "Ask a Question", "Case Breakdown", "Overview Dashboard"]
)

with tab1:
    people = run_query("MATCH (p:Person) RETURN p.name AS name ORDER BY name")
    names = [p["name"] for p in people]
    role_map = compute_roles()

    with st.container(border=True):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            view_mode = st.radio("View", ["Whole network", "Specific person", "Specific community", "Path between two people"], horizontal=True)
        with col_b:
            color_by = st.radio("Color by", ["Entity type", "Community"], horizontal=True)

        col_c, col_d = st.columns([1, 1])
        with col_c:
            layout = st.radio("Layout", ["Force-directed", "Hierarchical (by role)"], horizontal=True,
                               help="Hierarchical places Kingpins at the top, Intermediaries below them, and Associates at the bottom.")
        with col_d:
            people_only = st.checkbox("People only (hide locations/orgs/phones/vehicles)",
                                       value=(layout == "Hierarchical (by role)"))

        selected_person = None
        selected_comm = None

        use_timeline = st.checkbox("Filter by date range")
        date_range = None
        if use_timeline:
            all_dates = sorted(set(row["d"] for row in run_query("""
                MATCH ()-[r]->() WHERE r.date IS NOT NULL RETURN left(r.date,10) AS d
                UNION MATCH ()-[r]->() WHERE r.timestamp IS NOT NULL RETURN left(r.timestamp,10) AS d
            """)))
            if all_dates:
                start, end = st.select_slider("Date range", options=all_dates, value=(all_dates[0], all_dates[-1]))
                date_range = (start, end)

        if view_mode == "Path between two people":
            p1 = st.selectbox("From", names, key="path_from")
            p2 = st.selectbox("To", [n for n in names if n != p1], key="path_to")
            if st.button("Find connection path"):
                path_records, error = find_shortest_path(p1, p2)
                st.session_state["path_result"] = path_records
                if error:
                    st.error(f"Query failed: {error}")
                elif not path_records:
                    st.warning("No connection path found between these two people.")
            records = st.session_state.get("path_result", [])
        else:
            if view_mode == "Specific person":
                selected_person = st.selectbox("Select a person", names)
            elif view_mode == "Specific community":
                communities = run_query("MATCH (p:Person) RETURN DISTINCT p.community AS community ORDER BY community")
                comm_ids = [c["community"] for c in communities if c["community"] is not None]
                selected_comm = st.selectbox("Select a community/cell", comm_ids)

            query, params = build_graph_query(view_mode, selected_person, selected_comm, date_range, people_only)
            records = run_query_raw(query, params)

    if records:
        render_legend(color_by)
        render_graph(records, role_map, color_by=color_by, layout=layout)
    else:
        st.info("No data to display for this selection yet — try adjusting the filters above.")

    if view_mode == "Specific person" and selected_person:
        detail = run_query("""
            MATCH (p:Person {name: $name})
            RETURN p.pageRankScore AS influence, p.betweennessScore AS bridge_score,
                   p.community AS community, p.anomalyFlag AS flag
        """, {"name": selected_person})
        if detail:
            d = detail[0]
            role = role_map.get(selected_person, "Associate")
            c0, c1, c2, c3, c4 = st.columns(5)
            c0.metric("Role", role)
            c1.metric("Influence (PageRank)", f"{d['influence']:.3f}" if d["influence"] else "—")
            c2.metric("Bridge Score", f"{d['bridge_score']:.2f}" if d["bridge_score"] else "—")
            c3.metric("Cell/Community", d["community"] if d["community"] is not None else "—")
            c4.metric("Flag", d["flag"] or "None")

with tab2:
    st.header("Ask a Question")
    st.info("🚧 Gemini-powered natural language query — coming next once the API key is wired in.")

with tab3:
    st.header("Case Breakdown")
    st.info("🚧 Gemini-powered case summary + downloadable PDF report — coming next once the API key is wired in.")

with tab4:
    with st.container(border=True):
        st.markdown("##### Cell Leadership — PageRank by Community")
        influencers = pd.DataFrame(run_query("""
            MATCH (p:Person)
            RETURN p.name AS Person, p.community AS Community, p.pageRankScore AS Influence
            ORDER BY Community, Influence DESC
        """))
        show_table(influencers)

    with st.container(border=True):
        st.markdown("##### Known Intermediaries — Betweenness Centrality")
        intermediaries = pd.DataFrame(run_query("""
            MATCH (p:Person)
            RETURN p.name AS Person, p.betweennessScore AS Bridge_Score
            ORDER BY Bridge_Score DESC LIMIT 5
        """))
        show_table(intermediaries)

    with st.container(border=True):
        st.markdown("##### Active Flags")
        anomalies_df = pd.DataFrame(run_query("""
            MATCH (n) WHERE n.anomalyFlag IS NOT NULL
            RETURN labels(n)[0] AS Type, n.name AS Name, n.anomalyFlag AS Flag,
                   n.anomalyCallCount AS Calls, n.anomalyTxnCount AS Transactions
        """))
        if not anomalies_df.empty:
            anomalies_df.index = range(1, len(anomalies_df) + 1)
            styled = anomalies_df.style.apply(
                lambda row: [f'background-color: {ALERT}22' for _ in row], axis=1
            )
            st.dataframe(styled, use_container_width=True)
        else:
            st.write("No anomalies flagged.")
