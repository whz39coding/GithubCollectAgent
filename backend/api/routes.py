import re
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlmodel import Session, select

from backend.api.schemas import (
    AgentConfigOut,
    AgentConfigUpdate,
    ActionIngestPayload,
    ActionIngestResult,
    DashboardOverview,
    DashboardTrends,
    HealthOut,
    InsightDetail,
    InsightListItem,
    LanguagePoint,
    PaginatedInsights,
    RunLogOut,
    ScoreBucket,
    InsightUpdate,
    TrendPoint,
)
from backend.core.config import BACKEND_ROOT, PROJECT_ROOT, get_settings
from backend.database.engine import get_session
from backend.database.models import DailyInsight, Repository, RunLog, RunStatus
from backend.main import run as run_agent
from backend.services.action_ingest import ingest_action_payload, verify_ingest_signature


router = APIRouter(prefix="/api")


@router.post("/actions/ingest", response_model=ActionIngestResult)
async def ingest_action_results(
    request: Request,
    session: Session = Depends(get_session),
) -> ActionIngestResult:
    secret = get_settings().ingest_api_secret
    if not secret:
        raise HTTPException(status_code=503, detail="Actions ingest is not configured")

    timestamp = request.headers.get("X-Ingest-Timestamp", "")
    delivery_id = request.headers.get("X-Ingest-Delivery", "")
    signature = request.headers.get("X-Ingest-Signature", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", delivery_id):
        raise HTTPException(status_code=401, detail="Invalid ingest delivery")

    body = await request.body()
    if len(body) > 2_000_000:
        raise HTTPException(status_code=413, detail="Ingest payload is too large")
    if not verify_ingest_signature(
        secret,
        timestamp,
        delivery_id,
        body,
        signature,
    ):
        raise HTTPException(status_code=401, detail="Invalid ingest signature")

    try:
        payload = ActionIngestPayload.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    outcome = ingest_action_payload(session, delivery_id, payload)
    return ActionIngestResult(
        accepted=True,
        duplicate=outcome.duplicate,
        imported_count=outcome.imported_count,
    )


def run_to_out(run: RunLog | None) -> RunLogOut | None:
    if run is None:
        return None
    return RunLogOut(
        id=run.id or 0,
        status=str(run.status.value if hasattr(run.status, "value") else run.status),
        started_at=run.started_at,
        ended_at=run.ended_at,
        fetched_count=run.fetched_count,
        processed_count=run.processed_count,
        new_count=run.new_count,
        updated_count=run.updated_count,
        llm_call_count=run.llm_call_count,
        cache_hit_count=run.cache_hit_count,
        failed_count=run.failed_count,
        error_summary=run.error_summary,
    )


def latest_run(session: Session) -> RunLog | None:
    return session.exec(select(RunLog).order_by(RunLog.started_at.desc())).first()


@router.get("/health", response_model=HealthOut)
def health(session: Session = Depends(get_session)) -> HealthOut:
    return HealthOut(status="ok", database="ok", latest_run=run_to_out(latest_run(session)))


@router.get("/dashboard/overview", response_model=DashboardOverview)
def dashboard_overview(session: Session = Depends(get_session)) -> DashboardOverview:
    today = date.today()
    total_projects = session.exec(select(func.count(Repository.id))).one()
    today_new = session.exec(
        select(func.count(DailyInsight.id)).where(DailyInsight.insight_date == today, DailyInsight.is_new == True)
    ).one()
    today_updated = session.exec(
        select(func.count(DailyInsight.id)).where(
            DailyInsight.insight_date == today,
            DailyInsight.is_updated == True,
        )
    ).one()
    average_score = session.exec(select(func.avg(DailyInsight.score))).one() or 0
    run = latest_run(session)
    return DashboardOverview(
        total_projects=total_projects,
        today_new=today_new,
        today_updated=today_updated,
        average_score=round(float(average_score), 2),
        cache_hit_count=run.cache_hit_count if run else 0,
        latest_run=run_to_out(run),
    )


@router.get("/dashboard/trends", response_model=DashboardTrends)
def dashboard_trends(days: int = Query(default=30, ge=1, le=90), session: Session = Depends(get_session)) -> DashboardTrends:
    start_date = date.today() - timedelta(days=days - 1)
    insights = session.exec(
        select(DailyInsight).where(DailyInsight.insight_date >= start_date)
    ).all()

    daily_map: dict[date, dict[str, float]] = {}
    language_map: dict[tuple[date, str], int] = {}
    score_map: dict[int, int] = {score: 0 for score in range(1, 6)}
    for insight in insights:
        item = daily_map.setdefault(
            insight.insight_date,
            {"new_count": 0, "updated_count": 0, "score_sum": 0, "count": 0},
        )
        item["new_count"] += 1 if insight.is_new else 0
        item["updated_count"] += 1 if insight.is_updated else 0
        item["score_sum"] += insight.score
        item["count"] += 1
        language_key = (insight.insight_date, insight.language or "Unknown")
        language_map[language_key] = language_map.get(language_key, 0) + 1
        score_map[insight.score] = score_map.get(insight.score, 0) + 1

    daily = []
    for offset in range(days):
        current = start_date + timedelta(days=offset)
        item = daily_map.get(current, {"new_count": 0, "updated_count": 0, "score_sum": 0, "count": 0})
        count = item["count"] or 0
        daily.append(
            TrendPoint(
                date=current,
                new_count=int(item["new_count"]),
                updated_count=int(item["updated_count"]),
                average_score=round(float(item["score_sum"] / count), 2) if count else 0,
            )
        )

    languages = [
        LanguagePoint(date=key[0], language=key[1], count=count)
        for key, count in sorted(language_map.items(), key=lambda value: (value[0][0], value[0][1]))
    ]
    score_distribution = [ScoreBucket(score=score, count=count) for score, count in score_map.items()]
    return DashboardTrends(daily=daily, languages=languages, score_distribution=score_distribution)


@router.get("/insights", response_model=PaginatedInsights)
def list_insights(
    insight_date: date | None = Query(default=None, alias="date"),
    language: str | None = None,
    min_score: int | None = Query(default=None, ge=1, le=5),
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="score"),
    session: Session = Depends(get_session),
) -> PaginatedInsights:
    statement = select(DailyInsight)
    count_statement = select(func.count(DailyInsight.id))
    filters = []
    if insight_date:
        filters.append(DailyInsight.insight_date == insight_date)
    if language:
        filters.append(DailyInsight.language == language)
    if min_score:
        filters.append(DailyInsight.score >= min_score)
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(or_(DailyInsight.project_name.like(pattern), DailyInsight.summary.like(pattern)))
    for item in filters:
        statement = statement.where(item)
        count_statement = count_statement.where(item)

    sort_map = {
        "score": DailyInsight.score.desc(),
        "stars": DailyInsight.stars.desc(),
        "date": DailyInsight.insight_date.desc(),
        "created_at": DailyInsight.created_at.desc(),
    }
    statement = statement.order_by(sort_map.get(sort_by, DailyInsight.score.desc()))
    total = session.exec(count_statement).one()
    items = session.exec(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return PaginatedInsights(
        items=[to_list_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/insights/{insight_id}", response_model=InsightDetail)
def get_insight(insight_id: int, session: Session = Depends(get_session)) -> InsightDetail:
    insight = session.get(DailyInsight, insight_id)
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight not found")
    return InsightDetail(**to_list_item(insight).model_dump(), highlights=insight.highlights, details=insight.details, dev_ideas=insight.dev_ideas, risk_notes=insight.risk_notes, metrics=insight.metrics)


@router.post("/insights", response_model=InsightDetail)
def create_insight(payload: InsightUpdate, session: Session = Depends(get_session)) -> InsightDetail:
    insight = DailyInsight(
        repository_url=payload.repository_url,
        project_name=payload.project_name,
        summary=payload.summary,
        category=payload.category,
        language=payload.language,
        score=payload.score,
        stars=payload.stars,
        tech_stack=payload.tech_stack,
        business_potential=payload.business_potential,
        activity_level=payload.activity_level,
        community_health=payload.community_health,
        highlights=[],
        details=payload.summary,
        dev_ideas=[],
        risk_notes=[],
        metrics={},
    )
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return InsightDetail(**to_list_item(insight).model_dump(), highlights=insight.highlights, details=insight.details, dev_ideas=insight.dev_ideas, risk_notes=insight.risk_notes, metrics=insight.metrics)


@router.put("/insights/{insight_id}", response_model=InsightDetail)
def update_insight(insight_id: int, payload: InsightUpdate, session: Session = Depends(get_session)) -> InsightDetail:
    insight = session.get(DailyInsight, insight_id)
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight not found")

    insight.repository_url = payload.repository_url
    insight.project_name = payload.project_name
    insight.summary = payload.summary
    insight.category = payload.category
    insight.language = payload.language
    insight.score = payload.score
    insight.stars = payload.stars
    insight.tech_stack = payload.tech_stack
    insight.business_potential = payload.business_potential
    insight.activity_level = payload.activity_level
    insight.community_health = payload.community_health
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return InsightDetail(**to_list_item(insight).model_dump(), highlights=insight.highlights, details=insight.details, dev_ideas=insight.dev_ideas, risk_notes=insight.risk_notes, metrics=insight.metrics)


@router.delete("/insights/{insight_id}")
def delete_insight(insight_id: int, session: Session = Depends(get_session)) -> dict[str, bool]:
    insight = session.get(DailyInsight, insight_id)
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight not found")
    session.delete(insight)
    session.commit()
    return {"ok": True}


@router.get("/runs", response_model=list[RunLogOut])
def list_runs(limit: int = Query(default=20, ge=1, le=100), session: Session = Depends(get_session)) -> list[RunLogOut]:
    runs = session.exec(select(RunLog).order_by(RunLog.started_at.desc()).limit(limit)).all()
    return [item for item in (run_to_out(run) for run in runs) if item is not None]


@router.post("/runs/trigger")
def trigger_run(background_tasks: BackgroundTasks, session: Session = Depends(get_session)) -> dict[str, str]:
    # 检查是否有任务正在运行中
    running_task = session.exec(
        select(RunLog).where(RunLog.status == RunStatus.RUNNING)
    ).first()
    if running_task:
        raise HTTPException(
            status_code=409,
            detail="分析任务正在运行中，请勿重复触发"
        )

    # 异步触发运行
    background_tasks.add_task(run_agent)
    return {"message": "分析任务已在后台启动"}


@router.get("/settings/agent", response_model=AgentConfigOut)
def get_agent_config() -> AgentConfigOut:
    return AgentConfigOut(env=_read_env_file(), prompt=_read_prompt_file())


@router.put("/settings/agent", response_model=AgentConfigOut)
def update_agent_config(payload: AgentConfigUpdate) -> AgentConfigOut:
    _write_env_file(payload.env)
    _write_prompt_file(payload.prompt)

    # 动态清除 Pydantic Settings 的缓存，并重新加载环境变量
    from backend.core.config import get_settings, ENV_FILE
    from dotenv import load_dotenv
    get_settings.cache_clear()
    load_dotenv(dotenv_path=ENV_FILE, override=True)

    return AgentConfigOut(env=_read_env_file(), prompt=_read_prompt_file())


def to_list_item(insight: DailyInsight) -> InsightListItem:
    return InsightListItem(
        id=insight.id or 0,
        insight_date=insight.insight_date,
        repository_url=insight.repository_url,
        project_name=insight.project_name,
        score=insight.score,
        summary=insight.summary,
        category=insight.category,
        language=insight.language,
        stars=insight.stars,
        tech_stack=insight.tech_stack,
        activity_level=insight.activity_level,
        community_health=insight.community_health,
        business_potential=insight.business_potential,
        is_new=insight.is_new,
        is_updated=insight.is_updated,
        created_at=insight.created_at,
    )


def _read_env_file() -> dict[str, str]:
    env_path = BACKEND_ROOT / ".env"
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env_file(values: dict[str, str]) -> None:
    allowed_keys = [
        "SEND_MESSAGE",
        "CHECK_GITHUB_API",
        "GITHUB_TOKEN",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "FEISHU_WEBHOOK",
        "NOTIFIER_WEBHOOK",
        "TRENDING_LANGUAGE",
        "TRENDING_SINCE",
        "ANALYSIS_NUM",
        "README_MAX_LENGTH",
        "SAVE_README",
        "PROMPT_TEMPLATE_PATH",
        "LOG_DIR",
        "DATABASE_URL",
        "FINAL_REPORT_PATH",
        "HTTP_PROXY",
        "HTTPS_PROXY",
    ]
    lines = [f"{key}={values.get(key, '')}" for key in allowed_keys]
    (BACKEND_ROOT / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_prompt_file() -> str:
    prompt_path = PROJECT_ROOT / "Prompt.txt"
    return prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""


def _write_prompt_file(content: str) -> None:
    (PROJECT_ROOT / "Prompt.txt").write_text(content, encoding="utf-8")
