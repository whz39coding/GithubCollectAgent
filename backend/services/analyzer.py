import json

from loguru import logger
from openai import OpenAI
from pydantic import ValidationError
from tenacity import RetryError
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import Settings
from backend.schemas.project import AnalysisResult, GithubMetrics, ProjectWithReadme


class LLMAnalyzer:
    def __init__(self, settings: Settings) -> None:
        if not settings.llm_api_key:
            raise ValueError("未配置 LLM_API_KEY，无法执行大模型分析。")

        self.settings = settings
        self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        path = self.settings.prompt_template_path
        if not path.is_absolute():
            path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"找不到 Prompt 模板文件: {path}")
        return path.read_text(encoding="utf-8")

    def analyze_project(self, project: ProjectWithReadme) -> AnalysisResult:
        try:
            return self._analyze_project(project)
        except RetryError as exc:
            logger.warning("{} 多次分析失败，生成回退报告: {}", project.name, exc)
            return self._fallback_result(project, str(exc))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _analyze_project(self, project: ProjectWithReadme) -> AnalysisResult:
        logger.info("正在调用 LLM 分析: {}", project.name)
        prompt = self._build_prompt(project)

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": "你是一个只输出 JSON 格式的开源项目分析助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content or ""
        clean_content = raw_content.replace("```json", "").replace("```", "").strip()

        try:
            payload = json.loads(clean_content)
            payload["project_name"] = project.name
            payload["url"] = str(project.url)
            payload["stars"] = project.stars
            payload["metrics"] = project.metrics.model_dump()
            return AnalysisResult.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("LLM 返回结构不合法，将触发重试: {}", exc)
            raise

    def _build_prompt(self, project: ProjectWithReadme) -> str:
        schema = json.dumps(AnalysisResult.model_json_schema(), ensure_ascii=False)
        metrics = json.dumps(project.metrics.model_dump(), ensure_ascii=False, indent=2)
        base_prompt = self.prompt_template.replace("{readme_content}", project.readme_content)
        return (
            f"{base_prompt}\n\n"
            "### GitHub API 客观指标\n"
            f"{metrics}\n\n"
            "### 输出约束\n"
            "你必须只返回 JSON 对象，不要返回 Markdown。JSON 必须符合以下 Schema。"
            "如果 README 与 API 指标无法支撑某个判断，使用“未知”或“文档未提及”。\n"
            f"{schema}"
        )

    def _fallback_result(self, project: ProjectWithReadme, reason: str) -> AnalysisResult:
        return AnalysisResult(
            project_name=project.name,
            url=project.url,
            stars=project.stars,
            summary="大模型分析失败，已保留项目基础信息，建议稍后重试。",
            category=project.language or "未分类",
            score=3,
            tech_stack=[project.language] if project.language and project.language != "Unknown" else [],
            highlights=[],
            details=f"本次 LLM Pipeline 未能生成合法结构化结果。失败摘要：{reason[:300]}",
            dev_ideas=[],
            business_potential="未知",
            community_health="未知",
            activity_level="未知",
            risk_notes=["LLM 分析失败，结果为系统回退报告"],
            metrics=project.metrics or GithubMetrics(),
        )
