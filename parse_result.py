import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv



def format_message(projects_data):
    """
    将项目列表格式化为 Markdown 文本
    """
    if not projects_data:
        return "今日暂无热门项目分析。"

    # 1. 标题头
    date_str = datetime.now().strftime("%Y-%m-%d")
    msg = [f"## 🚀 GitHub 每日情报 ({date_str}) 关键词:Github自动发送助手 ", "---"]

    # 2. 遍历项目
    for idx, p in enumerate(projects_data, 1):
        # 提取数据，防止 key 不存在报错
        name = p.get('project_name', '未知项目')
        url = p.get('url', '#')
        score = p.get('score', 0)
        summary = p.get('summary', '暂无总结')
        desc = p.get('desc_detailed', '暂无详细介绍')

        # 拼接卡片内容
        msg.append(f"### {idx}. [{name}]({url})  {'⭐' * int(str(score))}")
        msg.append(f"**🏷 领域**: {p.get('category', '未分类')}")
        msg.append(f"**💡 一句话**: {summary}")
        msg.append(f"**📝 深度解析**: \n> {desc}")

        # 处理举一反三的灵感
        ideas = p.get('dev_ideas', [])
        if ideas:
            msg.append("**🧠 开发灵感 (举一反三)**:")
            for idea in ideas:
                msg.append(f"- {idea}")

        msg.append("---")

    msg.append(f"🤖 由 AI Agent 自动生成 | [查看源码](https://github.com/你的用户名/你的仓库名)")
    return "\n".join(msg)


def send_notification(content):
    """
    发送消息到飞书 Webhook
    """
    webhook_url = os.getenv("NOTIFIER_WEBHOOK",None)
    if not webhook_url:
        print("⚠️ 未配置 Webhook，跳过发送。")
        return

    headers = {'Content-Type': 'application/json'}

    # 飞书的消息体格式
    payload = {
        "msg_type": "interactive",  # 使用富文本卡片更漂亮，这里先用 markdown 兼容性好
        "card": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                }
            ],
            "header": {
                "template": "blue",
                "title": {
                    "content": "🔥 今日 GitHub 热门项目挖掘",
                    "tag": "plain_text"
                }
            }
        }
    }

    # 如果嫌 interactive 卡片复杂，可以直接用 text 类型：
    # payload = {"msg_type": "text", "content": {"text": content}}

    try:
        response = requests.post(
            webhook_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        if result.get("code") == 0:
            print("✅ 消息推送成功！")
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
