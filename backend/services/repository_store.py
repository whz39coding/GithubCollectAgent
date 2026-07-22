import hashlib
from datetime import date, datetime

from loguru import logger
from sqlmodel import Session, select

from backend.database.models import (
    AnalysisReport,
    DailyInsight,
    Repository,
    RunLog,
    RunStatus,
    TrendingSnapshot,
)
from backend.schemas.project import AnalysisResult, GithubMetrics, ProjectWithReadme, TrendingProject


class RepositoryStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start_run(self) -> RunLog:
        run_log = RunLog(status=RunStatus.RUNNING)
        self.session.add(run_log)
        self.session.commit()
        self.session.refresh(run_log)
        logger.info("RunLog 已创建: {}", run_log.id)
        return run_log

    def complete_run(
        self,
        run_log: RunLog,
        *,
        fetched_count: int,
        processed_count: int,
        new_count: int,
        updated_count: int,
        llm_call_count: int,
        cache_hit_count: int,
        failed_count: int,
    ) -> None:
        run_log.status = RunStatus.SUCCESS
        run_log.ended_at = datetime.utcnow()
        run_log.fetched_count = fetched_count
        run_log.processed_count = processed_count
        run_log.new_count = new_count
        run_log.updated_count = updated_count
        run_log.llm_call_count = llm_call_count
        run_log.cache_hit_count = cache_hit_count
        run_log.failed_count = failed_count
        self.session.add(run_log)
        self.session.commit()

    def fail_run(self, run_log: RunLog, error: Exception) -> None:
        run_log.status = RunStatus.FAILED
        run_log.ended_at = datetime.utcnow()
        run_log.error_summary = str(error)[:1000]
        self.session.add(run_log)
        self.session.commit()

    def record_trending_projects(self, projects: list[TrendingProject]) -> int:
        new_count = 0
        for project in projects:
            repository = self.get_repository(str(project.url))
            if repository is None:
                repository = Repository(
                    name=project.name,
                    url=str(project.url),
                    description=project.description,
                    language=project.language,
                )
                self.session.add(repository)
                new_count += 1
            else:
                repository.name = project.name
                repository.description = project.description
                repository.language = project.language
                repository.last_seen_at = datetime.utcnow()
                self.session.add(repository)

            self.session.add(
                TrendingSnapshot(
                    repository_url=str(project.url),
                    stars=project.stars,
                    rank=project.rank,
                )
            )

        self.session.commit()
        logger.info("Trending 入库完成，新项目 {} 个", new_count)
        return new_count

    def get_repository(self, repository_url: str) -> Repository | None:
        statement = select(Repository).where(Repository.url == repository_url)
        return self.session.exec(statement).first()

    def get_existing_report(self, repository_url: str) -> AnalysisReport | None:
        """查询数据库中已有的分析报告（仅按 URL 匹配）。"""
        statement = select(AnalysisReport).where(AnalysisReport.repository_url == repository_url)
        return self.session.exec(statement).first()

    def mark_project_state(
        self, project: ProjectWithReadme
    ) -> tuple["ProjectWithReadme", AnalysisReport | None]:
        """
        计算当前 README hash，查询数据库中已有报告，
        标记项目状态（is_new / is_updated），并返回 (project, existing_report)。
        调用方应使用返回的 existing_report 调用 get_cached_analysis，
        避免重复查库。
        """
        readme_hash = self.hash_readme(project.readme_content)
        existing_report = self.get_existing_report(str(project.url))

        # 若历史报告的 readme_hash 为空（旧数据），视为需要重新分析
        existing_hash = existing_report.readme_hash if existing_report else None
        is_new = existing_report is None
        is_updated = (
            existing_report is not None
            and bool(existing_hash)  # 旧 hash 为空也视为需更新
            and existing_hash != readme_hash
        )

        updated_project = project.model_copy(
            update={
                "readme_hash": readme_hash,
                "is_new": is_new,
                "is_updated": is_updated,
            }
        )
        return updated_project, existing_report

    def get_cached_analysis(
        self,
        project: ProjectWithReadme,
        existing_report: AnalysisReport | None,
    ) -> AnalysisResult | None:
        """
        根据 mark_project_state 返回的 existing_report 判断缓存是否命中。
        - is_new=True  → 无缓存，需要 LLM 分析
        - is_updated=True → README 有变化，需要重新 LLM 分析
        - 其他情况 → 直接复用已有报告，跳过 LLM
        """
        # 全新项目或 README 已更新，不使用缓存
        if project.is_new or project.is_updated:
            return None

        # existing_report 应该有值（is_new=False），防御性检查
        if existing_report is None:
            logger.warning("{} 状态异常：is_new=False 但 existing_report 为 None，将重新分析", project.name)
            return None

        logger.info("{} 命中分析缓存（hash 未变），跳过 LLM 调用", project.name)
        return AnalysisResult(
            project_name=existing_report.project_name,
            url=existing_report.repository_url,
            stars=existing_report.stars,
            summary=existing_report.summary,
            category=existing_report.category,
            score=existing_report.score,
            tech_stack=existing_report.tech_stack,
            highlights=existing_report.highlights,
            details=existing_report.details,
            dev_ideas=existing_report.dev_ideas,
            business_potential=existing_report.business_potential,
            community_health=existing_report.community_health,
            activity_level=existing_report.activity_level,
            risk_notes=existing_report.risk_notes,
            metrics=existing_report.metrics,
        )

    def save_analysis(self, result: AnalysisResult, project: ProjectWithReadme) -> None:
        if not project.readme_hash:
            project = project.model_copy(update={"readme_hash": self.hash_readme(project.readme_content)})

        metrics = self._metrics_to_dict(result)
        statement = select(AnalysisReport).where(AnalysisReport.repository_url == str(project.url))
        report = self.session.exec(statement).first()
        if report is None:
            report = AnalysisReport(
                repository_url=str(project.url),
                project_name=result.project_name,
                summary=result.summary,
                category=result.category,
                score=result.score,
                tech_stack=result.tech_stack,
                highlights=result.highlights,
                details=result.details,
                dev_ideas=result.dev_ideas,
                business_potential=result.business_potential,
                community_health=result.community_health,
                activity_level=result.activity_level,
                risk_notes=result.risk_notes,
                metrics=metrics,
                stars=result.stars,
                readme_hash=project.readme_hash,
            )
        else:
            report.project_name = result.project_name
            report.summary = result.summary
            report.category = result.category
            report.score = result.score
            report.tech_stack = result.tech_stack
            report.highlights = result.highlights
            report.details = result.details
            report.dev_ideas = result.dev_ideas
            report.business_potential = result.business_potential
            report.community_health = result.community_health
            report.activity_level = result.activity_level
            report.risk_notes = result.risk_notes
            report.metrics = metrics
            report.stars = result.stars
            report.readme_hash = project.readme_hash
            report.updated_at = datetime.utcnow()

        self.session.add(report)
        self.session.commit()

    def save_daily_insight(
        self,
        result: AnalysisResult,
        project: ProjectWithReadme,
        run_log: RunLog,
    ) -> None:
        statement = select(DailyInsight).where(
            DailyInsight.insight_date == date.today(),
            DailyInsight.repository_url == str(project.url),
        )
        metrics = self._metrics_to_dict(result)
        insight = self.session.exec(statement).first()
        if insight is None:
            insight = DailyInsight(
                insight_date=date.today(),
                run_id=run_log.id,
                repository_url=str(project.url),
                project_name=result.project_name,
                score=result.score,
                summary=result.summary,
                category=result.category,
                language=project.language,
                stars=result.stars,
                tech_stack=result.tech_stack,
                highlights=result.highlights,
                details=result.details,
                dev_ideas=result.dev_ideas,
                business_potential=result.business_potential,
                community_health=result.community_health,
                activity_level=result.activity_level,
                risk_notes=result.risk_notes,
                metrics=metrics,
                is_new=project.is_new,
                is_updated=project.is_updated,
            )
        else:
            insight.run_id = run_log.id
            insight.project_name = result.project_name
            insight.score = result.score
            insight.summary = result.summary
            insight.category = result.category
            insight.language = project.language
            insight.stars = result.stars
            insight.tech_stack = result.tech_stack
            insight.highlights = result.highlights
            insight.details = result.details
            insight.dev_ideas = result.dev_ideas
            insight.business_potential = result.business_potential
            insight.community_health = result.community_health
            insight.activity_level = result.activity_level
            insight.risk_notes = result.risk_notes
            insight.metrics = metrics
            insight.is_new = project.is_new
            insight.is_updated = project.is_updated
            insight.created_at = datetime.utcnow()

        self.session.add(insight)
        self.session.commit()

    @staticmethod
    def hash_readme(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _metrics_to_dict(result: AnalysisResult) -> dict:
        metrics = result.metrics or GithubMetrics()
        return metrics.model_dump()
