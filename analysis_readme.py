from openai import OpenAI
import json
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv('.env')

# LLM 设置
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

# GitHub 设置
# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# 检查必要配置
if not LLM_API_KEY:
    raise ValueError("❌ 错误: 未在 .env 文件中找到 LLM_API_KEY，请检查配置！")

# 初始化客户端
try:
    client = OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )
except Exception as e:
    raise ValueError("❌ 错误: 创建model实例失败，有可能是配置错误，请检查配置！", e)


def load_prompt_template(filename):
    """读取 Prompt 模板文件"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ 错误：找不到 Prompt 文件 {filename}")
        return None


def analyze_project(project_name, readme_content):
    """
    调用大模型分析 README
    :return: 解析后的字典 (Dict) 或 None
    """
    # print(f"🧠 AI 正在分析项目: {project_name} ...")

    template = load_prompt_template(filename='./Prompt.txt')
    if not template:
        return None

    # 填充 Prompt
    prompt = template.replace("{readme_content}", readme_content)

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个只输出 JSON 格式的开源项目分析助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 温度低一点，让输出更稳定
            response_format={"type": "json_object"}  # 强制 JSON 模式（部分模型支持）
        )

        raw_content = response.choices[0].message.content

        # --- 清洗数据 ---
        # 有时候 AI 会返回 ```json ... ```，我们需要去掉这些 Markdown 标记
        clean_content = raw_content.replace(
            "```json", "").replace("```", "").strip()

        # 解析 JSON 格式的字典
        analysis_result = json.loads(clean_content)

        # 把原始项目名加进去，方便后续使用
        analysis_result["project_name"] = project_name

        return analysis_result

    except json.JSONDecodeError:
        print(f"❌ JSON 解析失败，AI 返回的内容不是标准 JSON:\n{raw_content}")
        return None
    except Exception as e:
        print(f"❌ AI 调用失败: {e}")
        return None


if __name__ == "__main__":
    with open("./readme.md", 'r', encoding='utf-8') as f:
        readme_txt = f.read()[:10000]
    result = analyze_project("ruvnet/wifi-densepose", readme_txt)
    if result:
        print("\n✅ 分析成功！结果如下：")
        print(json.dumps(result, indent=4, ensure_ascii=False))
