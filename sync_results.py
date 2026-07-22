import os
import time
import uuid

import requests
from sqlmodel import Session, create_engine, select

from backend.api.schemas import ActionIngestPayload, ActionInsightImport, ActionRunImport
from backend.database.models import AnalysisReport, DailyInsight, Repository, RunLog, RunStatus
from backend.services.action_ingest import build_ingest_signature


engine = create_engine(
    os.getenv("ACTION_DATABASE_URL", "sqlite:///backend/database/agent.db")
)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def build_payload() -> ActionIngestPayload:
    with Session(engine) as session:
        run = session.exec(
            select(RunLog)
            .where(RunLog.status == RunStatus.SUCCESS)
            .order_by(RunLog.started_at.desc())
        ).first()
        if run is None or run.id is None or run.ended_at is None:
            raise RuntimeError("No completed agent run found to sync")

        records = session.exec(
            select(DailyInsight).where(DailyInsight.run_id == run.id)
        ).all()
        insights: list[ActionInsightImport] = []
        for insight in records:
            repository = session.exec(
                select(Repository).where(Repository.url == insight.repository_url)
            ).first()
            report = session.exec(
                select(AnalysisReport).where(
                    AnalysisReport.repository_url == insight.repository_url
                )
            ).first()
            if report is None:
                raise RuntimeError(
                    f"Missing analysis report for {insight.repository_url}"
                )

            insights.append(
                ActionInsightImport(
                    insight_date=insight.insight_date,
                    repository_url=insight.repository_url,
                    project_name=insight.project_name,
                    description=repository.description if repository else "",
                    language=insight.language,
                    stars=insight.stars,
                    summary=insight.summary,
                    category=insight.category,
                    score=insight.score,
                    tech_stack=insight.tech_stack,
                    highlights=insight.highlights,
                    details=insight.details,
                    dev_ideas=insight.dev_ideas,
                    business_potential=insight.business_potential,
                    community_health=insight.community_health,
                    activity_level=insight.activity_level,
                    risk_notes=insight.risk_notes,
                    metrics=insight.metrics,
                    readme_hash=report.readme_hash,
                    created_at=insight.created_at,
                )
            )

        return ActionIngestPayload(
            run=ActionRunImport(
                started_at=run.started_at,
                ended_at=run.ended_at,
                fetched_count=run.fetched_count,
                processed_count=run.processed_count,
                llm_call_count=run.llm_call_count,
                cache_hit_count=run.cache_hit_count,
                failed_count=run.failed_count,
            ),
            insights=insights,
        )


def main() -> None:
    base_url = require_env("ACTION_SYNC_URL").rstrip("/")
    secret = require_env("ACTION_SYNC_SECRET")
    delivery_id = os.getenv("ACTION_DELIVERY_ID", "").strip() or str(uuid.uuid4())
    timestamp = str(int(time.time()))
    body = build_payload().model_dump_json().encode("utf-8")
    signature = build_ingest_signature(secret, timestamp, delivery_id, body)

    response = requests.post(
        f"{base_url}/api/actions/ingest",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Ingest-Timestamp": timestamp,
            "X-Ingest-Delivery": delivery_id,
            "X-Ingest-Signature": signature,
        },
        timeout=60,
    )
    response.raise_for_status()
    print(f"Server import result: {response.json()}")


if __name__ == "__main__":
    main()
