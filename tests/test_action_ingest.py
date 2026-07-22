import unittest
from datetime import date, datetime

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.api.schemas import ActionIngestPayload, ActionInsightImport, ActionRunImport
from backend.database.models import AnalysisReport, DailyInsight, IngestDelivery, Repository, RunLog
from backend.services.action_ingest import (
    build_ingest_signature,
    ingest_action_payload,
    verify_ingest_signature,
)


class SignatureTests(unittest.TestCase):
    def test_signature_rejects_tampering_and_expired_requests(self) -> None:
        secret = "test-secret"
        timestamp = "1000"
        delivery_id = "github-123-1"
        body = b'{"ok":true}'
        signature = build_ingest_signature(secret, timestamp, delivery_id, body)

        self.assertTrue(
            verify_ingest_signature(
                secret,
                timestamp,
                delivery_id,
                body,
                signature,
                now=1100,
            )
        )
        self.assertFalse(
            verify_ingest_signature(
                secret,
                timestamp,
                delivery_id,
                b'{"ok":false}',
                signature,
                now=1100,
            )
        )
        self.assertFalse(
            verify_ingest_signature(
                secret,
                timestamp,
                delivery_id,
                body,
                signature,
                now=1400,
            )
        )


class IngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

    @staticmethod
    def payload(readme_hash: str = "hash-v1") -> ActionIngestPayload:
        now = datetime(2026, 7, 21, 1, 0, 0)
        return ActionIngestPayload(
            run=ActionRunImport(
                started_at=now,
                ended_at=now,
                fetched_count=10,
                processed_count=1,
                llm_call_count=1,
            ),
            insights=[
                ActionInsightImport(
                    insight_date=date(2026, 7, 21),
                    repository_url="https://github.com/example/project",
                    project_name="example/project",
                    description="Example project",
                    language="Python",
                    stars=100,
                    summary="Summary",
                    score=4,
                    details="Details",
                    readme_hash=readme_hash,
                    created_at=now,
                )
            ],
        )

    def test_ingest_is_idempotent_and_upserts_server_records(self) -> None:
        with Session(self.engine) as session:
            first = ingest_action_payload(session, "delivery-1", self.payload())
            duplicate = ingest_action_payload(session, "delivery-1", self.payload())

            self.assertFalse(first.duplicate)
            self.assertEqual(first.imported_count, 1)
            self.assertTrue(duplicate.duplicate)
            self.assertEqual(len(session.exec(select(Repository)).all()), 1)
            self.assertEqual(len(session.exec(select(AnalysisReport)).all()), 1)
            self.assertEqual(len(session.exec(select(DailyInsight)).all()), 1)
            self.assertEqual(len(session.exec(select(RunLog)).all()), 1)
            self.assertEqual(len(session.exec(select(IngestDelivery)).all()), 1)

    def test_new_delivery_updates_readme_state(self) -> None:
        with Session(self.engine) as session:
            ingest_action_payload(session, "delivery-1", self.payload("hash-v1"))
            outcome = ingest_action_payload(session, "delivery-2", self.payload("hash-v2"))

            insight = session.exec(select(DailyInsight)).one()
            report = session.exec(select(AnalysisReport)).one()
            self.assertFalse(outcome.duplicate)
            self.assertTrue(insight.is_updated)
            self.assertEqual(report.readme_hash, "hash-v2")


if __name__ == "__main__":
    unittest.main()
