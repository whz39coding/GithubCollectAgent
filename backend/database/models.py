from datetime import date, datetime
from enum import Enum

from sqlalchemy import Column, JSON, TEXT
from sqlmodel import Field, SQLModel


class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Repository(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str = Field(unique=True, index=True)
    description: str = Field(default="", sa_column=Column(TEXT))
    language: str = "Unknown"
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)


class TrendingSnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    repository_url: str = Field(foreign_key="repository.url", index=True)
    snapshot_date: date = Field(default_factory=date.today, index=True)
    stars: int = 0
    forks: int = 0
    rank: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnalysisReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    repository_url: str = Field(foreign_key="repository.url", unique=True, index=True)
    project_name: str
    summary: str = Field(sa_column=Column(TEXT))
    category: str = "未分类"
    score: int = 3
    tech_stack: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    highlights: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    details: str = Field(sa_column=Column(TEXT))
    dev_ideas: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    business_potential: str = Field(default="文档未提及", sa_column=Column(TEXT))
    community_health: str = "未知"
    activity_level: str = "未知"
    risk_notes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    metrics: dict = Field(default_factory=dict, sa_column=Column(JSON))
    stars: int = 0
    readme_hash: str = Field(index=True)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DailyInsight(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    insight_date: date = Field(default_factory=date.today, index=True)
    run_id: int | None = Field(default=None, foreign_key="runlog.id", index=True)
    repository_url: str = Field(foreign_key="repository.url", index=True)
    project_name: str = Field(index=True)
    score: int = 3
    summary: str = Field(sa_column=Column(TEXT))
    category: str = "未分类"
    language: str = "Unknown"
    stars: int = 0
    tech_stack: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    highlights: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    details: str = Field(sa_column=Column(TEXT))
    dev_ideas: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    business_potential: str = Field(default="文档未提及", sa_column=Column(TEXT))
    community_health: str = "未知"
    activity_level: str = "未知"
    risk_notes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    metrics: dict = Field(default_factory=dict, sa_column=Column(JSON))
    is_new: bool = False
    is_updated: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RunLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: RunStatus = Field(default=RunStatus.RUNNING, index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    fetched_count: int = 0
    processed_count: int = 0
    new_count: int = 0
    updated_count: int = 0
    llm_call_count: int = 0
    cache_hit_count: int = 0
    failed_count: int = 0
    error_summary: str | None = None


class IngestDelivery(SQLModel, table=True):
    delivery_id: str = Field(primary_key=True, max_length=128)
    received_at: datetime = Field(default_factory=datetime.utcnow)
