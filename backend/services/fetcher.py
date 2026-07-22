from pathlib import Path

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import Settings
from backend.schemas.project import GithubMetrics, ProjectWithReadme, TrendingProject
from backend.services.github_api import GithubApiClient
from backend.services.preprocessor import ReadmePreprocessor


class GithubFetcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.github_api = GithubApiClient(settings)
        self.preprocessor = ReadmePreprocessor(settings.readme_max_length)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _request_readme(self, repo_name: str) -> requests.Response:
        headers = {
            "User-Agent": "Mozilla/5.0 (Python Script)",
            "Accept": "application/vnd.github.v3.raw",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"token {self.settings.github_token}"

        proxies = None
        if self.settings.http_proxy:
            proxies = {
                "http": self.settings.http_proxy,
                "https": self.settings.https_proxy or self.settings.http_proxy,
            }

        response = requests.get(
            f"https://api.github.com/repos/{repo_name}/readme",
            headers=headers,
            timeout=10,
            proxies=proxies,
        )
        if response.status_code in {403, 404}:
            return response
        response.raise_for_status()
        return response

    def fetch_readme(self, project: TrendingProject) -> ProjectWithReadme | None:
        logger.info("正在获取 README: {}", project.name)
        response = self._request_readme(project.name)

        if response.status_code == 404:
            logger.warning("{} 没有 README 文件，跳过", project.name)
            return None
        if response.status_code == 403:
            logger.warning("爬取readm.md时候, GitHub API 请求受限，建议配置 GITHUB_TOKEN")
            return None

        raw_content = response.text
        if self.settings.save_readme:
            output_path = Path(f"readme_{project.name.replace('/', '_')}.md")
            output_path.write_text(raw_content, encoding="utf-8")
            logger.info("README 已保存到 {}", output_path)

        content = self.preprocessor.clean(raw_content)
        if self.settings.check_github_api:
            try:
                metrics = self.github_api.fetch_metrics(project.name)
            except Exception as exc:
                logger.warning("{} 爬取github api时, GitHub API 指标获取失败，使用空指标继续分析: {}", project.name, exc)
                metrics = GithubMetrics()
        else:
            logger.info("跳过github api 请求只爬取README.md")
            metrics = GithubMetrics()

        return ProjectWithReadme(
            **project.model_dump(),
            readme_content=content,
            raw_readme_length=len(raw_content),
            metrics=metrics,
        )
