import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.schemas.project import TrendingProject


class GithubCollector:
    def __init__(self) -> None:
        self.base_url = "https://github.com/trending"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _request_trending_page(self, url: str) -> str:
        from backend.core.config import get_settings
        settings = get_settings()
        proxies = None
        if settings.http_proxy:
            proxies = {
                "http": settings.http_proxy,
                "https": settings.https_proxy or settings.http_proxy,
            }
        try:
            logger.info("准备发起请求: {}, 使用代理: {}", url, proxies)
            response = requests.get(url, headers=self.headers, timeout=10, proxies=proxies)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            logger.error("网络请求失败! 错误类型: {}, 详细信息: {}", type(exc).__name__, repr(exc))
            raise

    def get_trending_projects(self, language: str = "python", since: str = "daily") -> list[TrendingProject]:
        if language:
            url = f"{self.base_url}/{language}?since={since}"
        else:
            url = f"{self.base_url}?since={since}"

        logger.info("正在抓取 GitHub Trending: {}", url)
        html = self._request_trending_page(url)
        soup = BeautifulSoup(html, "html.parser")

        projects: list[TrendingProject] = []
        for rank, row in enumerate(soup.select("article.Box-row"), 1):
            try:
                h2_tag = row.select_one("h2.h3 a")
                if h2_tag is None:
                    continue

                raw_name = h2_tag.get_text(strip=True)
                project_name = raw_name.replace(" ", "")
                project_url = "https://github.com" + h2_tag["href"]

                desc_tag = row.select_one("p.col-9")
                lang_tag = row.select_one('span[itemprop="programmingLanguage"]')
                star_tag = row.select_one('a[href$="/stargazers"]')

                projects.append(
                    TrendingProject(
                        name=project_name,
                        url=project_url,
                        description=desc_tag.get_text(strip=True) if desc_tag else "暂无描述",
                        stars=star_tag.get_text(strip=True) if star_tag else 0,
                        language=lang_tag.get_text(strip=True) if lang_tag else "Unknown",
                        rank=rank,
                    )
                )
            except Exception as exc:
                logger.warning("解析 Trending 第 {} 行失败: {}", rank, exc)

        logger.info("成功抓取 {} 个 Trending 项目", len(projects))
        return projects
