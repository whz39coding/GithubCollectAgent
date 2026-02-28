import time
from collect import get_trending_projects
from fetch_readme import get_readme
from analysis_readme import analyze_project
import time
import json
from parse_result import format_message, send_notification

MAX_LENGTH = 10000
SAVE_FLAG = False
def main(language="python", since="daily", max_length=MAX_LENGTH,save_flag=SAVE_FLAG):
    print(f"🚀{time.time()}的任务开始 ...\n")

    # 1. 获取榜单
    print(f"🚀{time.time()}开始获取榜单 ...\n")
    projects = get_trending_projects(language, since)
    target_projects = projects[:3]  # 测试时只跑 2 个，省钱省时间

    final_report = []

    for project in target_projects:
        print(f"\n🔍 处理项目：{project.name}")

        # 2. 获取素材
        # 注意：这里传入 config 里的 Token
        readme_content = get_readme(project.name,max_length,save_flag)

        if not readme_content:
            print(f"⚠️ {project.name}无 README, 跳过分析")
            continue

        # 3. AI 分析
        print(f"🧠 AI 正在分析项目：{project.name} ...")
        analysis = analyze_project(project.name, readme_content)

        if analysis:
            # 将基础信息和 AI 分析结果合并（可选）
            analysis["url"] = project.url
            analysis["stars"] = project.stars
            final_report.append(analysis)
            print("✅ 分析完成！")

        time.sleep(1)  # 避免并发过快

    # 可以本地保存最终结果
    print(f"\n🏁 全部完成！生成了 {len(final_report)} 份报告：\n")
    with open("final_report.txt", "w", encoding="utf-8") as f:
        for i, report in enumerate(final_report):
            f.write(f"{i+1}. {report['project_name']}:\n")
            f.write(f"   star⭐: {report['stars']} 语言📦: {report['tech_stack']} \n")
            f.write(f"   📚 项目简介: {report['summary']} \n")
            f.write(f"   ✨ 亮点: {report.get('highlights')}\n")
            f.write(f"   📝 详细报告: {report['details']}\n")
            f.write(f"   🛠️ 衍生灵感 : {report['dev_ideas']}\n")
            f.write(f"   🔗 项目链接: {report['url']}\n")
        f.write("\n \n")
    print("✅ 报告已保存为 final_report.txt")
    # 组装与发送
    if final_report:
        print("\n📦 正在生成报告并推送...")
        markdown_content = format_message(final_report)
        send_notification(markdown_content)
    else:
        print("⚠️ 本次运行没有生成有效报告。")


if __name__ == "__main__":
    main()



