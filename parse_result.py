import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv


def format_message(projects_data):
    """
    将项目列表格式化为飞书友好的 Markdown 文本
    """
    if not projects_data:
        return "🤷 今日暂无热门项目分析。"

    date_str = datetime.now().strftime("%Y-%m-%d")

    msg = [
        f"🚀 **GitHub 每日情报 · {date_str}**",
        "关键词：**Github自动发送助手**",
        ""
    ]

    for idx, p in enumerate(projects_data, 1):
        name = p.get('project_name', '未知项目')
        url = p.get('url', '解析错误')
        score = int(float(p.get('score', 3)))
        summary = p.get('summary', '暂无总结')
        desc = p.get('details', '暂无详细介绍')

        msg.extend([
            f"🔥 **TOP {idx}｜[{name}]({url})**",
            f"⭐ **推荐指数**：{'⭐' * score}",
            f"🏷 **领域**：{p.get('category', '未分类')}  \n💻 **技术**：{'   -  '.join(p.get('tech_stack', ['无']))}",
            f"✨ **亮点**：{'   -  '.join(p.get('highlights', '无'))}",
            f"💡 **一句话总结**：{summary}",
            f"📝 **详细解读**：{desc}",
        ])

        ideas = p.get('dev_ideas', [])
        if ideas:
            msg.append("🧠 **可延伸方向：**")
            for idea in ideas:
                msg.append(f"   - {idea}")

        msg.append("")

    msg.append("🤖 由 AI Agent 自动分析生成")

    return "\n".join(msg)


def send_notification(content):
    """
    发送消息到飞书 Webhook（使用富卡片结构化排版，显示更美观）
    """
    webhook_url = os.getenv("NOTIFIER_WEBHOOK")
    if not webhook_url:
        print("⚠️ 未配置 Webhook，跳过发送。")
        return

    headers = {'Content-Type': 'application/json'}

    # 将正文拆成多段，增强阅读体验
    blocks = []
    for block in content.strip().split("\n\n"):
        blocks.append({
            "tag": "markdown",
            "content": block
        })
        blocks.append({"tag": "hr"})  # 分割线

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "content": "🔥 今日 GitHub 热门项目挖掘",
                    "tag": "plain_text"
                }
            },
            "elements": blocks[:-1]  # 去掉最后一条 hr
        }
    }

    try:
        response = requests.post(
            webhook_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("code") == 0:
            print("✅ 飞书消息推送成功！")
        else:
            print(f"❌ 推送失败: {result}")
    except Exception as e:
        print(f"❌ 推送异常: {e}")
if __name__ == "__main__":
    # 加载 .env 文件
    load_dotenv('.env') 
    # 测试用的 projects_data 示例
    projects_data = [
        {
            "project_name": "whz39coding/GithubCollectAgent",
            "url": "https://github.com/whz39coding/GithubCollectAgent",
            "score": 5,
            "summary": "一个自动化收集和分析GitHub热门项目的AI代理工具",
            "desc_detailed": "该项目使用Python开发，结合网络爬虫和AI模型，自动抓取GitHub Trending页面上的热门项目，并对项目README进行智能分析，生成结构化报告。",
            "category": "AI工具",
            "dev_ideas": [
                "增加对多个编程语言的支持",
                "集成更多社交平台的数据",
                "添加项目趋势预测功能"
            ]
        },
        {
            "project_name": "microsoft/TypeScript",
            "url": "https://github.com/microsoft/TypeScript",
            "score": 4,
            "summary": "JavaScript的超集，添加了静态类型检查",
            "desc_detailed": "TypeScript是微软开发的开源编程语言，扩展了JavaScript，增加了可选的静态类型和基于类的面向对象编程。",
            "category": "编程语言",
            "dev_ideas": [
                "构建TypeScript代码质量分析工具",
                "开发TypeScript性能优化插件",
                "创建TS/JS迁移辅助工具"
            ]
        }
    ]

    print("\n📦 正在生成报告并推送...")
    markdown_content = format_message(projects_data)
    send_notification(markdown_content)
