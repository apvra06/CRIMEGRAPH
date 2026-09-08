import axios from 'axios';
import {
  GraphDataResponse,
  CaseOverviewStats,
  PersonDetail,
  ShortestPathResponse,
  LeadershipItem,
  IntermediaryItem,
  AnomalyItem,
  AskQuestionResponse,
  CaseBreakdownResponse,
  HealthResponse
} from '../types';

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // System Health
  getHealth: async (): Promise<HealthResponse> => {
    const res = await apiClient.get<HealthResponse>('/health');
    return res.data;
  },

  // Case Overview & Analytics
  getCaseStats: async (): Promise<CaseOverviewStats> => {
    const res = await apiClient.get<CaseOverviewStats>('/analytics/case-stats');
    return res.data;
  },

  getLeadership: async (): Promise<LeadershipItem[]> => {
    const res = await apiClient.get<LeadershipItem[]>('/analytics/leadership');
    return res.data;
  },

  getIntermediaries: async (): Promise<IntermediaryItem[]> => {
    const res = await apiClient.get<IntermediaryItem[]>('/analytics/intermediaries');
    return res.data;
  },

  getAnomalies: async (): Promise<AnomalyItem[]> => {
    const res = await apiClient.get<AnomalyItem[]>('/analytics/anomalies');
    return res.data;
  },

  // Graph Endpoints
  getGraphData: async (params: {
    view_mode?: string;
    person?: string;
    community?: number;
    start_date?: string;
    end_date?: string;
    people_only?: boolean;
    color_by?: string;
  }): Promise<GraphDataResponse> => {
    const res = await apiClient.get<GraphDataResponse>('/graph/data', { params });
    return res.data;
  },

  getPeople: async (): Promise<string[]> => {
    const res = await apiClient.get<string[]>('/graph/people');
    return res.data;
  },

  getCommunities: async (): Promise<number[]> => {
    const res = await apiClient.get<number[]>('/graph/communities');
    return res.data;
  },

  getDateRange: async (): Promise<{ start_date: string | null; end_date: string | null }> => {
    const res = await apiClient.get<{ start_date: string | null; end_date: string | null }>('/graph/date-range');
    return res.data;
  },

  getPersonDetail: async (name: string): Promise<PersonDetail> => {
    const res = await apiClient.get<PersonDetail>(`/graph/person/${encodeURIComponent(name)}`);
    return res.data;
  },

  findShortestPath: async (p1: string, p2: string): Promise<ShortestPathResponse> => {
    const res = await apiClient.post<ShortestPathResponse>('/graph/shortest-path', { p1, p2 });
    return res.data;
  },

  // AI & Case Breakdown
  askQuestion: async (question: string): Promise<AskQuestionResponse> => {
    const res = await apiClient.post<AskQuestionResponse>('/ai/ask', { question });
    return res.data;
  },

  getCaseBreakdown: async (): Promise<CaseBreakdownResponse> => {
    const res = await apiClient.get<CaseBreakdownResponse>('/ai/breakdown');
    return res.data;
  },
};

