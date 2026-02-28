import requests
import base64


def get_readme(repo_name, max_length=10000,save_flag=False,token=None):
    """
    获取 GitHub 项目的 README 内容
    :param repo_name: 项目全名，例如 "owner/repo"
    :param token: GitHub Personal Access Token (可选，建议加上以提高限流阈值)
    :return: README 的纯文本内容 (String)
    """
    api_url = f"https://api.github.com/repos/{repo_name}/readme"

    headers = {
        "User-Agent": "Mozilla/5.0 (Python Script)",
        # 这个 Header 让 GitHub 直接返回 Markdown 原始内容，而不是 JSON
        "Accept": "application/vnd.github.v3.raw"
    }

    # 如果你有 Token，加进去可以把每小时限制从 60 次提升到 5000 次
    if token:
        headers["Authorization"] = f"token {token}"

    print(f"📥 正在获取 README: {repo_name} ...")

    try:
        response = requests.get(api_url, headers=headers, timeout=10)

        # 404 代表没有 README
        if response.status_code == 404:
            print(f"⚠️ {repo_name} 没有 README 文件。")
            return None

        # 403 代表请求太频繁（被限流了）
        if response.status_code == 403:
            print("🚫 API 请求受限！请稍后再试，或配置 GitHub Token。")
            return None

        response.raise_for_status()

        content = response.text

        if save_flag:
            with open(f"readme_{repo_name}.md", "w", encoding="utf-8") as f:
                f.write(content)
                print(f"✅ README_{repo_name} 保存成功！")
        

        # --- 关键步骤：清洗与截断 ---
        # 很多 README 非常长，包含大量代码或 Base64 图片，会消耗大量 AI Token
        # 我们只取前 maxlength 个字符，足够 AI 理解项目是做什么的了
        if len(content) > max_length:
            print(f"   ✂️ 内容太长 ({len(content)} 字)，已截取前{max_length}字...")
            content = content[:max_length] + "\n...剩余readme内容已省略,根据已有的信息总结。"

        return content

    except requests.RequestException as e:
        print(f"❌ 获取 README 失败: {e}")
        return None


# --- 单元测试 ---
if __name__ == "__main__":
    # 随便找个热门项目测试一下
    test_repo = "ruvnet/wifi-densepose"
    # 如果你有 Token，可以在这里填入： token="ghp_xxxx..."
    content = get_readme(test_repo)

    if content:
        print("\n✅ 获取成功！内容预览：")
        print("=" * 40)
        print(content[:500])  # 只打印前500字看看效果
        print("=" * 40)
