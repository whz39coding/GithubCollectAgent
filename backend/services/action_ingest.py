import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from backend.api.schemas import ActionIngestPayload
from backend.database.models import (
    AnalysisReport,
    DailyInsight,
    IngestDelivery,
    Repository,
    RunLog,
    RunStatus,
)


MAX_CLOCK_SKEW_SECONDS = 300


def build_ingest_signature(
    secret: str,
    timestamp: str,
    delivery_id: str,
    body: bytes,
) -> str:
    message = timestamp.encode("ascii") + b"\n" + delivery_id.encode("utf-8") + b"\n" + body
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_ingest_signature(
    secret: str,
    timestamp: str,
    delivery_id: str,
    body: bytes,
    signature: str,
    *,
    now: int | None = None,
) -> bool:
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False

    current_time = int(time.time()) if now is None else now
    if abs(current_time - sent_at) > MAX_CLOCK_SKEW_SECONDS:
        return False

    expected = build_ingest_signature(secret, timestamp, delivery_id, body)
    return hmac.compare_digest(expected, signature)


@dataclass(frozen=True)
class IngestOutcome:
    duplicate: bool
    imported_count: int


def ingest_action_payload(
    session: Session,
    delivery_id: str,
    payload: ActionIngestPayload,
) -> IngestOutcome:
    if session.get(IngestDelivery, delivery_id) is not None:
        return IngestOutcome(duplicate=True, imported_count=0)

    remote_run = RunLog(
        status=RunStatus.SUCCESS,
        started_at=payload.run.started_at,
        ended_at=payload.run.ended_at,
        fetched_count=payload.run.fetched_count,
        processed_count=len(payload.insights),
        llm_call_count=payload.run.llm_call_count,
        cache_hit_count=payload.run.cache_hit_count,
        failed_count=payload.run.failed_count,
    )
    session.add(remote_run)
    session.flush()

    new_count = 0
    updated_count = 0
    now = datetime.utcnow()

    for item in payload.insights:
        repository = session.exec(
            select(Repository).where(Repository.url == item.repository_url)
        ).first()
        if repository is None:
            repository = Repository(
                name=item.project_name,
                url=item.repository_url,
                description=item.description,
                language=item.language,
            )
            session.add(repository)
        else:
            repository.name = item.project_name
            repository.description = item.description
            repository.language = item.language
            repository.last_seen_at = now

        report = session.exec(
            select(AnalysisReport).where(
                AnalysisReport.repository_url == item.repository_url
            )
        ).first()
        is_new = report is None
        is_updated = report is not None and report.readme_hash != item.readme_hash
        new_count += int(is_new)
        updated_count += int(is_updated)

        if report is None:
            report = AnalysisReport(
                repository_url=item.repository_url,
                project_name=item.project_name,
                summary=item.summary,
                category=item.category,
                score=item.score,
                tech_stack=item.tech_stack,
                highlights=item.highlights,
                details=item.details,
                dev_ideas=item.dev_ideas,
                business_potential=item.business_potential,
                community_health=item.community_health,
                activity_level=item.activity_level,
                risk_notes=item.risk_notes,
                metrics=item.metrics,
                stars=item.stars,
                readme_hash=item.readme_hash,
            )
        else:
            report.project_name = item.project_name
            report.summary = item.summary
            report.category = item.category
            report.score = item.score
            report.tech_stack = item.tech_stack
            report.highlights = item.highlights
            report.details = item.details
            report.dev_ideas = item.dev_ideas
            report.business_potential = item.business_potential
            report.community_health = item.community_health
            report.activity_level = item.activity_level
            report.risk_notes = item.risk_notes
            report.metrics = item.metrics
            report.stars = item.stars
            report.readme_hash = item.readme_hash
            report.updated_at = now
        session.add(report)

        insight = session.exec(
            select(DailyInsight).where(
                DailyInsight.insight_date == item.insight_date,
                DailyInsight.repository_url == item.repository_url,
            )
        ).first()
        if insight is None:
            insight = DailyInsight(
                insight_date=item.insight_date,
                repository_url=item.repository_url,
                project_name=item.project_name,
                summary=item.summary,
                details=item.details,
            )

        insight.run_id = remote_run.id
        insight.project_name = item.project_name
        insight.score = item.score
        insight.summary = item.summary
        insight.category = item.category
        insight.language = item.language
        insight.stars = item.stars
        insight.tech_stack = item.tech_stack
        insight.highlights = item.highlights
        insight.details = item.details
        insight.dev_ideas = item.dev_ideas
        insight.business_potential = item.business_potential
        insight.community_health = item.community_health
        insight.activity_level = item.activity_level
        insight.risk_notes = item.risk_notes
        insight.metrics = item.metrics
        insight.is_new = is_new
        insight.is_updated = is_updated
        insight.created_at = item.created_at
        session.add(insight)

    remote_run.new_count = new_count
    remote_run.updated_count = updated_count
    session.add(remote_run)
    session.add(IngestDelivery(delivery_id=delivery_id))
    session.commit()
    return IngestOutcome(duplicate=False, imported_count=len(payload.insights))
