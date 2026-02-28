import requests
from bs4 import BeautifulSoup
import csv
import time

# 定义一个简单的数据类，方便后续传递数据


class ProjectInfo:
    def __init__(self, name, url, description, stars, language):
        self.name = name            # 项目名称 (例如: owner/repo)
        self.url = url              # 项目完整链接
        self.description = description  # 项目原始描述
        self.stars = stars          # 总 Star 数
        self.language = language    # 编程语言

    def __repr__(self):
        return f"项目名称📦: {self.name} | star数🌟: {self.stars} | 项目语言\
🔧:  {self.language}\n   项目描述📖: {self.description}\n"


def get_trending_projects(language="python", since="daily"):
    """
    抓取 GitHub Trending 页面
    :param language: 语言 (例如: python, javascript, go, 或 '' 代表所有语言)
    :param since: 周期 (daily, weekly, monthly)
    :return: List[ProjectInfo]
    """
    base_url = "https://github.com/trending"
    if language:
        url = f"{base_url}/{language}?since={since}"
    else:
        url = f"{base_url}?since={since}"

    print(f"🔄 正在抓取: {url} ...")

    headers = {
        # 这一步很关键！伪装成浏览器，否则会被 GitHub 拦截
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 如果状态码不是 200，抛出异常
    except requests.RequestException as e:
        print(f"❌ 请求失败(魔法打开了吗,小子😘😘😘),详细信息为: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # 获取所有的项目卡片
    project_rows = soup.select('article.Box-row')

    projects_list = []

    for row in project_rows:
        try:
            # 1. 获取项目名称和链接
            h2_tag = row.select_one('h2.h3 a')
            # get_text(strip=True) 会自动去除换行符和首尾空格
            # 这里的 text 可能是 "owner / repo"，我们需要去掉中间的空格
            raw_name = h2_tag.get_text(strip=True)
            project_name = raw_name.replace(' ', '')
            project_url = "https://github.com" + h2_tag['href']

            # 2. 获取描述 (有的项目可能没有描述)
            desc_tag = row.select_one('p.col-9')
            description = desc_tag.get_text(strip=True) if desc_tag else "暂无描述"

            # 3. 获取编程语言 (有的项目可能没有标注语言)
            lang_tag = row.select_one('span[itemprop="programmingLanguage"]')
            language = lang_tag.get_text(strip=True) if lang_tag else "Unknown"

            # 4. 获取 Star 数 (总星数)
            # GitHub 结构里，Star 数通常在链接 href 包含 /stargazers 的 a 标签里
            star_tag = row.select_one('a[href$="/stargazers"]')
            # 清理数字中的逗号和换行，例如 "1,234" -> 1234
            stars = star_tag.get_text(strip=True).replace(
                ',', '') if star_tag else "0"

            # 创建对象并添加到列表
            project = ProjectInfo(project_name, project_url,
                                  description, stars, language)
            projects_list.append(project)

        except Exception as e:
            print(f"⚠️ 解析某一行时出错: {e}")
            continue

    return projects_list


# --- 调试入口 ---
if __name__ == "__main__":
    # 测试：抓取 Python 日榜
    hot_projects = get_trending_projects(language="python", since="daily")

    print(f"\n✅ 成功抓取到 {len(hot_projects)} 个项目：\n")

    for p in hot_projects[:5]:  # 为了展示方便，只打印前5个
        print(p)
        print("-" * 50)
