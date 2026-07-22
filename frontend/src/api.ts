import axios from 'axios';

export const api = axios.create({
  baseURL: '/api',
  timeout: 15000
});

export interface RunLog {
  id: number;
  status: string;
  started_at: string;
  ended_at?: string | null;
  fetched_count: number;
  processed_count: number;
  new_count: number;
  updated_count: number;
  llm_call_count: number;
  cache_hit_count: number;
  failed_count: number;
  error_summary?: string | null;
}

export interface Overview {
  total_projects: number;
  today_new: number;
  today_updated: number;
  average_score: number;
  cache_hit_count: number;
  latest_run?: RunLog | null;
}

export interface Trends {
  daily: Array<{ date: string; new_count: number; updated_count: number; average_score: number }>;
  languages: Array<{ date: string; language: string; count: number }>;
  score_distribution: Array<{ score: number; count: number }>;
}

export interface Insight {
  id: number;
  insight_date: string;
  repository_url: string;
  project_name: string;
  score: number;
  summary: string;
  category: string;
  language: string;
  stars: number;
  tech_stack: string[];
  activity_level: string;
  community_health: string;
  business_potential: string;
  is_new: boolean;
  is_updated: boolean;
  created_at: string;
}

export interface InsightDetail extends Insight {
  highlights: string[];
  details: string;
  dev_ideas: string[];
  risk_notes: string[];
  metrics: Record<string, unknown>;
}

export interface InsightPage {
  items: Insight[];
  total: number;
  page: number;
  page_size: number;
}

export interface AgentConfig {
  env: Record<string, string>;
  prompt: string;
}

export interface InsightPayload {
  repository_url: string;
  project_name: string;
  summary: string;
  category: string;
  language: string;
  score: number;
  stars: number;
  tech_stack: string[];
  business_potential: string;
  activity_level: string;
  community_health: string;
}

export const fetchOverview = async () => (await api.get<Overview>('/dashboard/overview')).data;
export const fetchTrends = async () => (await api.get<Trends>('/dashboard/trends')).data;
export const fetchRuns = async () => (await api.get<RunLog[]>('/runs')).data;
export const fetchInsights = async (params: Record<string, unknown>) =>
  (await api.get<InsightPage>('/insights', { params })).data;
export const fetchInsight = async (id: number) => (await api.get<InsightDetail>(`/insights/${id}`)).data;
export const createInsight = async (payload: InsightPayload) => (await api.post<InsightDetail>('/insights', payload)).data;
export const updateInsight = async (id: number, payload: InsightPayload) => (await api.put<InsightDetail>(`/insights/${id}`, payload)).data;
export const deleteInsight = async (id: number) => (await api.delete(`/insights/${id}`)).data;
export const fetchAgentConfig = async () => (await api.get<AgentConfig>('/settings/agent')).data;
export const updateAgentConfig = async (payload: AgentConfig) => (await api.put<AgentConfig>('/settings/agent', payload)).data;
export const triggerRun = async () => (await api.post<{ message: string }>('/runs/trigger')).data;
