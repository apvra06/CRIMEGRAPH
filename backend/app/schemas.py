from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class NodeStyle(BaseModel):
    shape: str
    color: str
    size: int
    borderWidth: int = 1
    glyph: str = "●"
    level: Optional[int] = None


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    role: Optional[str] = None
    pageRankScore: Optional[float] = None
    betweennessScore: Optional[float] = None
    community: Optional[int] = None
    anomalyFlag: Optional[str] = None
    title: str = ""
    style: NodeStyle
    level: Optional[int] = None


class GraphEdge(BaseModel):
    id: str
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    type: str
    title: str = ""
    date: Optional[str] = None
    timestamp: Optional[str] = None
    color: str = "#555555"
    width: int = 1

    class Config:
        populate_by_name = True


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int
    is_mock: bool = False


class CaseOverviewStats(BaseModel):
    suspects: int
    cells: int
    anomalies: int
    top_influencer: Optional[str] = None
    top_influencer_score: Optional[float] = None
    is_mock: bool = False


class PersonDetail(BaseModel):
    name: str
    role: str
    influence: Optional[float] = None
    bridge_score: Optional[float] = None
    community: Optional[int] = None
    flag: Optional[str] = None
    connections_count: int = 0
    connected_entities: List[Dict[str, Any]] = []


class ShortestPathRequest(BaseModel):
    p1: str
    p2: str


class ShortestPathResponse(BaseModel):
    found: bool
    path_nodes: List[GraphNode] = []
    path_edges: List[GraphEdge] = []
    message: Optional[str] = None


class LeadershipItem(BaseModel):
    person: str
    community: Optional[int] = None
    influence: Optional[float] = None


class IntermediaryItem(BaseModel):
    person: str
    bridge_score: Optional[float] = None


class AnomalyItem(BaseModel):
    type: str
    name: str
    flag: str
    calls: Optional[int] = None
    transactions: Optional[int] = None


class AskQuestionRequest(BaseModel):
    question: str


class AskQuestionResponse(BaseModel):
    answer: str
    citations: List[str] = []
    related_entities: List[str] = []


class CaseBreakdownResponse(BaseModel):
    case_id: str
    title: str
    summary: str
    key_suspects: List[Dict[str, Any]]
    high_risk_cells: List[Dict[str, Any]]
    anomalies_detected: List[Dict[str, Any]]
    recommendations: List[str]


class HealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    neo4j_uri: str
    mode: str

