from datetime import datetime, timedelta, timezone

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import Settings
from backend.schemas.project import GithubMetrics


class GithubApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = "https://api.github.com"

    @property
    def headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "GithubInsightAgent",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _get_json(self, path: str, params: dict[str, str | int] | None = None) -> dict | list:
        proxies = None
        if self.settings.http_proxy:
            proxies = {
                "http": self.settings.http_proxy,
                "https": self.settings.https_proxy or self.settings.http_proxy,
            }

        response = requests.get(
            f"{self.base_url}{path}",
            headers=self.headers,
            params=params,
            timeout=10,
            proxies=proxies,
        )
        if response.status_code == 404:
            return {}
        if response.status_code == 403:
            logger.warning("GitHub API 请求受限: {}", path)
            return {}
        response.raise_for_status()
        return response.json()

    def fetch_metrics(self, repo_name: str) -> GithubMetrics:
        logger.info("正在获取 GitHub API 指标: {}", repo_name)
        repo_data = self._safe_dict(self._get_json(f"/repos/{repo_name}"))
        languages = self._safe_dict(self._get_json(f"/repos/{repo_name}/languages"))
        latest_release = self._safe_dict(self._get_json(f"/repos/{repo_name}/releases/latest"))

        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        commits = self._safe_list(
            self._get_json(
                f"/repos/{repo_name}/commits",
                params={"since": since, "per_page": 100},
            )
        )
        closed_issues = self._count_recent_closed_issues(repo_name)

        return GithubMetrics(
            forks=int(repo_data.get("forks_count") or 0),
            open_issues=int(repo_data.get("open_issues_count") or 0),
            closed_issues_recent=closed_issues,
            commits_recent=len(commits),
            latest_release=latest_release.get("tag_name") or latest_release.get("name"),
            pushed_at=repo_data.get("pushed_at"),
            language_distribution=self._normalize_languages(languages),
        )

    def _count_recent_closed_issues(self, repo_name: str) -> int:
        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        query = f"repo:{repo_name} is:issue is:closed closed:>={since}"
        payload = self._safe_dict(
            self._get_json(
                "/search/issues",
                params={"q": query, "per_page": 1},
            )
        )
        return int(payload.get("total_count") or 0)

    @staticmethod
    def _normalize_languages(languages: dict) -> dict[str, float]:
        total = sum(int(value) for value in languages.values())
        if total <= 0:
            return {}
        return {
            str(language): round((int(bytes_count) / total) * 100, 2)
            for language, bytes_count in languages.items()
        }

    @staticmethod
    def _safe_dict(value: dict | list) -> dict:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _safe_list(value: dict | list) -> list:
        return value if isinstance(value, list) else []
