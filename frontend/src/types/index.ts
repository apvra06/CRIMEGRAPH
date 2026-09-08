export interface NodeStyle {
  shape: string;
  color: string;
  size: number;
  borderWidth?: number;
  glyph?: string;
  level?: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  role?: string | null;
  pageRankScore?: number | null;
  betweennessScore?: number | null;
  community?: number | null;
  anomalyFlag?: string | null;
  title: string;
  style: NodeStyle;
  level?: number | null;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  type: string;
  title: string;
  date?: string | null;
  timestamp?: string | null;
  color: string;
  width: number;
}

export interface GraphDataResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
  is_mock: boolean;
}

export interface CaseOverviewStats {
  suspects: number;
  cells: number;
  anomalies: number;
  top_influencer?: string | null;
  top_influencer_score?: number | null;
  is_mock: boolean;
}

export interface ConnectedEntity {
  entity: string;
  type?: string;
  relationship: string;
  direction?: string;
}

export interface PersonDetail {
  name: string;
  role: string;
  influence?: number | null;
  bridge_score?: number | null;
  community?: number | null;
  flag?: string | null;
  connections_count: number;
  connected_entities: ConnectedEntity[];
}

export interface ShortestPathResponse {
  found: boolean;
  path_nodes: GraphNode[];
  path_edges: GraphEdge[];
  message?: string | null;
}

export interface LeadershipItem {
  person: string;
  community?: number | null;
  influence?: number | null;
}

export interface IntermediaryItem {
  person: string;
  bridge_score?: number | null;
}

export interface AnomalyItem {
  type: string;
  name: string;
  flag: string;
  calls?: number | null;
  transactions?: number | null;
}

export interface AskQuestionResponse {
  answer: string;
  citations: string[];
  related_entities: string[];
}

export interface KeySuspect {
  name: string;
  role: string;
  threat_level: string;
  notes: string;
}

export interface HighRiskCell {
  cell_id: number;
  leader: string;
  influence_score: number;
  status: string;
}

export interface AnomalyDetected {
  entity: string;
  type: string;
  signature: string;
  metric: string;
}

export interface CaseBreakdownResponse {
  case_id: string;
  title: string;
  summary: string;
  key_suspects: KeySuspect[];
  high_risk_cells: HighRiskCell[];
  anomalies_detected: AnomalyDetected[];
  recommendations: string[];
}

export interface HealthResponse {
  status: string;
  neo4j_connected: boolean;
  neo4j_uri: string;
  mode: string;
}

