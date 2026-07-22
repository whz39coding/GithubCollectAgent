from pydantic import BaseModel, Field, HttpUrl, field_validator


class GithubMetrics(BaseModel):
    forks: int = 0
    open_issues: int = 0
    closed_issues_recent: int = 0
    commits_recent: int = 0
    latest_release: str | None = None
    pushed_at: str | None = None
    language_distribution: dict[str, float] = Field(default_factory=dict)


class TrendingProject(BaseModel):
    name: str
    url: HttpUrl
    description: str = "暂无描述"
    stars: int = 0
    language: str = "Unknown"
    rank: int | None = None

    @field_validator("stars", mode="before")
    @classmethod
    def parse_stars(cls, value: int | str) -> int:
        if isinstance(value, int):
            return value
        cleaned = value.replace(",", "").strip()
        return int(cleaned or 0)


class ProjectWithReadme(TrendingProject):
    readme_content: str = Field(min_length=1)
    raw_readme_length: int = 0
    readme_hash: str | None = None
    is_new: bool = False
    is_updated: bool = False
    metrics: GithubMetrics = Field(default_factory=GithubMetrics)


class AnalysisResult(BaseModel):
    project_name: str
    url: HttpUrl | None = None
    stars: int = 0
    summary: str
    category: str = "未分类"
    score: int = Field(default=3, ge=1, le=5)
    tech_stack: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    details: str
    dev_ideas: list[str] = Field(default_factory=list)
    business_potential: str = "文档未提及"
    community_health: str = "未知"
    activity_level: str = "未知"
    risk_notes: list[str] = Field(default_factory=list)
    metrics: GithubMetrics = Field(default_factory=GithubMetrics)

    @field_validator("score", mode="before")
    @classmethod
    def normalize_score(cls, value: int | float | str) -> int:
        try:
            return max(1, min(5, int(float(value))))
        except (TypeError, ValueError):
            return 3

    @field_validator("tech_stack", "highlights", "dev_ideas", "risk_notes", mode="before")
    @classmethod
    def normalize_string_list(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return [value] if value.strip() else []
