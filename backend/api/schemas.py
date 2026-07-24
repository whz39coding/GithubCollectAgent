from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class RunLogOut(BaseModel):
    id: int
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    fetched_count: int
    processed_count: int
    new_count: int
    updated_count: int
    llm_call_count: int
    cache_hit_count: int
    failed_count: int
    error_summary: str | None = None


class DashboardOverview(BaseModel):
    total_projects: int
    today_new: int
    today_updated: int
    average_score: float
    cache_hit_count: int
    latest_run: RunLogOut | None = None


class TrendPoint(BaseModel):
    date: date
    new_count: int
    updated_count: int
    average_score: float


class LanguagePoint(BaseModel):
    date: date
    language: str
    count: int


class ScoreBucket(BaseModel):
    score: int
    count: int


class DashboardTrends(BaseModel):
    daily: list[TrendPoint]
    languages: list[LanguagePoint]
    score_distribution: list[ScoreBucket]


class InsightListItem(BaseModel):
    id: int
    insight_date: date
    repository_url: str
    project_name: str
    score: int
    summary: str
    category: str
    language: str
    stars: int
    tech_stack: list[str]
    activity_level: str
    community_health: str
    business_potential: str
    is_new: bool
    is_updated: bool
    created_at: datetime


class InsightDetail(InsightListItem):
    highlights: list[str]
    details: str
    dev_ideas: list[str]
    risk_notes: list[str]
    metrics: dict[str, Any]


class PaginatedInsights(BaseModel):
    items: list[InsightListItem]
    total: int
    page: int
    page_size: int


class HealthOut(BaseModel):
    status: str
    database: str
    latest_run: RunLogOut | None = None


class AgentConfigOut(BaseModel):
    env: dict[str, str]
    prompt: str


class AgentConfigUpdate(BaseModel):
    env: dict[str, str]
    prompt: str


class InsightUpdate(BaseModel):
    repository_url: str
    project_name: str
    summary: str
    category: str = "未分类"
    language: str = "Unknown"
    score: int = 3
    stars: int = 0
    tech_stack: list[str] = []
    business_potential: str = "文档未提及"
    activity_level: str = "未知"
    community_health: str = "未知"
