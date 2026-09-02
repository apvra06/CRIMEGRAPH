"""
Streamlit dashboard for the AI-powered criminal network analysis prototype.

Run with: streamlit run app.py
Requires config.py (copy config_template.py and fill in real credentials).
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from neo4j import GraphDatabase
from pyvis.network import Network
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

st.set_page_config(page_title="Crime Network Analysis", layout="wide", page_icon="◆")

# --------------------------------------------------------- Design tokens ---
# Palette: deep navy-slate base (not pure black) with amber as the primary
# data accent and teal as secondary — an analyst-terminal identity rather
# than the generic near-black + single bright accent look. Burnt-orange is
# reserved exclusively for anomaly flags so it always signals danger and
# never doubles as decoration.
BG = "#0B0F1A"
SURFACE = "#131826"
BORDER = "#232A3D"
AMBER = "#C99A3C"
TEAL = "#4FB6AC"
ALERT = "#D9480F"
TEXT_MUTED = "#8A93A6"

ENTITY_COLORS = {
    "Person": AMBER,
    "Location": TEAL,
    "Organization": "#8C7BC9",
    "PhoneNumber": "#9CC97B",
    "Vehicle": "#C97B9C",
}
COMMUNITY_PALETTE = ["#C99A3C", "#4FB6AC", "#8C7BC9", "#9CC97B", "#C97B9C", "#6B93C9", "#C9A05E", "#5EC9AE"]
ANOMALY_COLOR = ALERT
MUTED_COLOR = "#3A4152"

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
    .legend-dot {{ display: inline-block; width: 8px; height: 8px; margin-right: 6px; }}

    section[data-testid="stSidebar"] {{ background-color: {SURFACE}; border-right: 1px solid {BORDER}; }}

    div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; }}
</style>
""", unsafe_allow_html=True)


def show_table(df):
    """Displays a dataframe with a 1-indexed row number instead of pandas'
    default 0-indexed row labels — matches how an investigator would
    actually number a briefing list."""
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


def build_graph_query(view_mode, selected_person=None, selected_comm=None, date_range=None):
    where_clauses = []
    params = {}
    if date_range:
        where_clauses.append(
            "((r.date IS NOT NULL AND left(r.date,10) >= $start AND left(r.date,10) <= $end) "
            "OR (r.timestamp IS NOT NULL AND left(r.timestamp,10) >= $start AND left(r.timestamp,10) <= $end))"
        )
        params["start"], params["end"] = date_range

    if view_mode == "Specific person":
        base = "MATCH (n:Person {name: $name})-[r]-(m)"
        params["name"] = selected_person
    elif view_mode == "Specific community":
        base = "MATCH (n:Person {community: $comm})-[r]-(m)"
        params["comm"] = selected_comm
    else:
        base = "MATCH (n)-[r]-(m)"

    query = base
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " RETURN n, r, m LIMIT 300"
    return query, params


def render_graph(records, color_by="Entity type", height=650):
    net = Network(height=f"{height}px", width="100%", bgcolor="#0E1117", font_color="#EEEEEE", directed=False)
    net.barnes_hut(gravity=-4000, central_gravity=0.35, spring_length=110, spring_strength=0.045, damping=0.15)
    added_nodes = set()

    def node_color(node):
        if node.get("anomalyFlag"):
            return ANOMALY_COLOR
        node_type = next(iter(node.labels), "Unknown")
        if color_by == "Community" and node_type == "Person" and node.get("community") is not None:
            return COMMUNITY_PALETTE[node.get("community") % len(COMMUNITY_PALETTE)]
        if color_by == "Community":
            return MUTED_COLOR
        return ENTITY_COLORS.get(node_type, "#999999")

    def flatten(record):
        """Yields (node_or_rel) items, unwrapping Path objects if present."""
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
            title_lines = [f"{node_type}: {label}"]
            if item.get("pageRankScore") is not None:
                title_lines.append(f"Influence (PageRank): {item.get('pageRankScore'):.3f}")
            if item.get("betweennessScore") is not None:
                title_lines.append(f"Bridge score: {item.get('betweennessScore'):.2f}")
            if item.get("community") is not None:
                title_lines.append(f"Cell/Community: {item.get('community')}")
            if item.get("anomalyFlag"):
                title_lines.append(f"⚠ FLAGGED: {item.get('anomalyFlag')}")
            size = 15
            if item.get("pageRankScore") is not None:
                size = item.get("pageRankScore")  # vis.js scales via 'value' automatically
            net.add_node(node_id, label=label, title="\n".join(title_lines),
                         color=node_color(item), value=size)
            added_nodes.add(node_id)

    for item in all_items:
        if hasattr(item, "type") and hasattr(item, "start_node"):  # Relationship
            if item.start_node.element_id in added_nodes and item.end_node.element_id in added_nodes:
                date_info = item.get("date") or item.get("timestamp") or ""
                net.add_edge(item.start_node.element_id, item.end_node.element_id,
                             title=f"{item.type}  {date_info}", color="#555555", width=1)

    net.set_options("""
    {
      "nodes": {"scaling": {"min": 12, "max": 42}, "font": {"size": 14}},
      "physics": {"stabilization": {"enabled": true, "iterations": 250}},
      "interaction": {"hover": true, "navigationButtons": true, "keyboard": true}
    }
    """)

    net.save_graph("_graph.html")
    with open("_graph.html", "r", encoding="utf-8") as f:
        html = f.read()
    # Best-effort: auto-fit the view once physics settles, so the user isn't
    # forced to manually zoom out to see the whole graph.
    html = html.replace(
        "</body>",
        "<script>network.once('stabilizationIterationsDone', function() { network.fit({animation:true}); });</script></body>"
    )
    components.html(html, height=height + 20)


def render_legend(color_by):
    items = ENTITY_COLORS.items() if color_by == "Entity type" else \
        [(f"Community {i}", c) for i, c in enumerate(COMMUNITY_PALETTE[:4])]
    html = "".join(
        f'<span class="legend-item"><span class="legend-dot" style="background:{color}"></span>{name}</span>'
        for name, color in items
    )
    html += f'<span class="legend-item"><span class="legend-dot" style="background:{ANOMALY_COLOR}"></span>⚠ Flagged anomaly</span>'
    st.markdown(html, unsafe_allow_html=True)


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

    with st.container(border=True):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            view_mode = st.radio("View", ["Whole network", "Specific person", "Specific community", "Path between two people"], horizontal=True)
        with col_b:
            color_by = st.radio("Color by", ["Entity type", "Community"], horizontal=True)

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

        records = []
        if view_mode == "Path between two people":
            p1 = st.selectbox("From", names, key="path_from")
            p2 = st.selectbox("To", [n for n in names if n != p1], key="path_to")
            if st.button("Find connection path"):
                records = run_query_raw(
                    "MATCH path = shortestPath((a:Person {name:$p1})-[*..6]-(b:Person {name:$p2})) RETURN path",
                    {"p1": p1, "p2": p2},
                )
                if not records:
                    st.warning("No connection path found between these two people.")
        else:
            if view_mode == "Specific person":
                selected_person = st.selectbox("Select a person", names)
            elif view_mode == "Specific community":
                communities = run_query("MATCH (p:Person) RETURN DISTINCT p.community AS community ORDER BY community")
                comm_ids = [c["community"] for c in communities if c["community"] is not None]
                selected_comm = st.selectbox("Select a community/cell", comm_ids)

        query, params = build_graph_query(view_mode, selected_person, selected_comm, date_range)
        records = run_query_raw(query, params)

    if records:
        render_legend(color_by)
        render_graph(records, color_by=color_by)
    else:
        st.info("No data to display for this selection yet — try adjusting the filters above.")

    # Person detail side panel
    if view_mode == "Specific person" and selected_person:
        detail = run_query("""
            MATCH (p:Person {name: $name})
            RETURN p.pageRankScore AS influence, p.betweennessScore AS bridge_score,
                   p.community AS community, p.anomalyFlag AS flag
        """, {"name": selected_person})
        if detail:
            d = detail[0]
            c1, c2, c3, c4 = st.columns(4)
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
