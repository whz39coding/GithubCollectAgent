import time
from datetime import datetime

from loguru import logger
from sqlmodel import Session

from backend.core.config import Settings, get_settings
from backend.core.logger import setup_logger
from backend.database.engine import engine, init_db
from backend.schemas.project import AnalysisResult
from backend.services.analyzer import LLMAnalyzer
from backend.services.collector import GithubCollector
from backend.services.fetcher import GithubFetcher
from backend.services.notifier import FeishuNotifier
from backend.services.repository_store import RepositoryStore


def write_final_report(results: list[AnalysisResult], settings: Settings) -> None:
    lines: list[str] = []
    for index, report in enumerate(results, 1):
        lines.extend(
            [
                f"{index}. {report.project_name}:",
                f"   star: {report.stars}  语言/技术: {', '.join(report.tech_stack)}",
                f"   项目简介: {report.summary}",
                f"   亮点: {'; '.join(report.highlights)}",
                f"   详细报告: {report.details}",
                f"   活跃度: {report.activity_level}  社区健康: {report.community_health}",
                f"   商业潜力: {report.business_potential}",
                f"   GitHub 指标: 近30天提交 {report.metrics.commits_recent}, Open Issues {report.metrics.open_issues}, Forks {report.metrics.forks}",
                f"   衍生灵感: {'; '.join(report.dev_ideas)}",
                f"   项目链接: {report.url}",
                "",
            ]
        )

    settings.final_report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("报告已保存到 {}", settings.final_report_path)


def run() -> list[AnalysisResult]:
    setup_logger()
    settings = get_settings()
    init_db()

    logger.info("{} 的任务开始", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    collector = GithubCollector()
    fetcher = GithubFetcher(settings)
    analyzer: LLMAnalyzer | None = None
    notifier = FeishuNotifier(settings)

    with Session(engine) as session:
        store = RepositoryStore(session)
        run_log = store.start_run()

        fetched_count = 0
        processed_count = 0
        new_count = 0
        updated_count = 0
        llm_call_count = 0
        cache_hit_count = 0
        failed_count = 0

        try:
            projects = collector.get_trending_projects(
                language=settings.trending_language,
                since=settings.trending_since,
            )
            fetched_count = len(projects)
            new_count = store.record_trending_projects(projects)
            target_projects = projects[: settings.analysis_num]
            logger.info("本次计划分析 {} 个项目", len(target_projects))

            results: list[AnalysisResult] = []
            push_results: list[AnalysisResult] = []
            for project in target_projects:
                logger.info("开始处理项目: {}", project.name)
                project_with_readme = fetcher.fetch_readme(project)
                if project_with_readme is None:
                    failed_count += 1
                    continue

                project_with_readme, existing_report = store.mark_project_state(project_with_readme)
                cached_result = store.get_cached_analysis(project_with_readme, existing_report)
                if cached_result is not None:
                    cache_hit_count += 1
                    results.append(cached_result)
                    processed_count += 1
                    store.save_daily_insight(cached_result, project_with_readme, run_log)
                    continue

                try:
                    if analyzer is None:
                        analyzer = LLMAnalyzer(settings)
                    llm_call_count += 1
                    result = analyzer.analyze_project(project_with_readme)
                    store.save_analysis(result, project_with_readme)
                    store.save_daily_insight(result, project_with_readme, run_log)
                    results.append(result)
                    processed_count += 1
                    if project_with_readme.is_new or project_with_readme.is_updated:
                        push_results.append(result)
                    if project_with_readme.is_updated:
                        updated_count += 1
                    logger.info("{} 分析完成", project.name)
                except Exception as exc:
                    failed_count += 1
                    logger.exception("{} 分析失败: {}", project.name, exc)

                time.sleep(1)

            logger.info("全部完成，本次生成 {} 份报告", len(results))
            write_final_report(results, settings)
            logger.info(f"send_message_flag:{settings.send_message_flag}")
            if push_results and settings.send_message_flag:
                notifier.send_message(push_results)
            else:
                logger.info("没有新项目或 README 更新项目，跳过推送")

            store.complete_run(
                run_log,
                fetched_count=fetched_count,
                processed_count=processed_count,
                new_count=new_count,
                updated_count=updated_count,
                llm_call_count=llm_call_count,
                cache_hit_count=cache_hit_count,
                failed_count=failed_count,
            )
            return results
        except Exception as exc:
            store.fail_run(run_log, exc)
            raise


if __name__ == "__main__":
    run()
