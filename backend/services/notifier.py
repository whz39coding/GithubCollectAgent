from datetime import datetime

import requests
from loguru import logger

from backend.core.config import Settings
from backend.schemas.project import AnalysisResult


class FeishuNotifier:
    def __init__(self, settings: Settings) -> None:
        self.webhook_url = settings.notifier_webhook

    def send_message(self, results: list[AnalysisResult]) -> None:
        if not self.webhook_url:
            logger.warning("未配置 FEISHU_WEBHOOK/NOTIFIER_WEBHOOK，跳过推送")
            return

        content = self._format_to_markdown(results)
        blocks = []
        for block in content.strip().split("\n\n"):
            blocks.append({"tag": "markdown", "content": block})
            blocks.append({"tag": "hr"})

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"content": "今日 GitHub 热门项目挖掘", "tag": "plain_text"},
                },
                "elements": blocks[:-1],
            },
        }

        response = requests.post(
            self.webhook_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code") == 0:
            logger.info("飞书消息推送成功")
        else:
            logger.warning("飞书消息推送返回异常: {}", result)

    def _format_to_markdown(self, results: list[AnalysisResult]) -> str:
        if not results:
            return "今日暂无热门项目分析。"

        msg = [
            f"**GitHub 每日情报 · {datetime.now().strftime('%Y-%m-%d')}**",
            "关键词：**Github自动发送助手**",
            "",
        ]

        for index, result in enumerate(results, 1):
            metrics = result.metrics
            languages = "   -  ".join(
                f"{name} {percent}%" for name, percent in metrics.language_distribution.items()
            )
            msg.extend(
                [
                    f"**TOP {index}｜[{result.project_name}]({result.url})**",
                    f"**推荐指数**：{'⭐' * result.score}",
                    f"**领域**：{result.category}  \n**技术**：{'   -  '.join(result.tech_stack) or '无'}",
                    f"**活跃度**：{result.activity_level}  \n**社区健康**：{result.community_health}",
                    f"**客观指标**：近30天提交 {metrics.commits_recent} ｜ Open Issues {metrics.open_issues} ｜ 近30天关闭 Issues {metrics.closed_issues_recent} ｜ Forks {metrics.forks}",
                    f"**语言占比**：{languages or '未知'}",
                    f"**商业潜力**：{result.business_potential}",
                    f"**亮点**：{'   -  '.join(result.highlights) or '无'}",
                    f"**一句话总结**：{result.summary}",
                    f"**详细解读**：{result.details}",
                ]
            )
            if result.risk_notes:
                msg.append(f"**风险提示**：{'   -  '.join(result.risk_notes)}")
            if result.dev_ideas:
                msg.append("**可延伸方向：**")
                msg.extend(f"   - {idea}" for idea in result.dev_ideas)
            msg.append("")

        msg.append("由 AI Agent 自动分析生成")
        return "\n".join(msg)
