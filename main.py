import os
import requests
import feedparser
from google import genai
from google.genai import types

# 环境变量初始化（自动读取 GitHub Actions Secrets 里的密钥）
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")

# 初始化 Gemini 客户端
client = genai.Client(api_key=GEMINI_API_KEY)

# 5大核心领域赛道及代表性高质量信源（可按需自行扩展）
TRACKS = [
    {
        "name": "AI与前沿技术",
        "sources": [
            "https://karpathy.github.io/feed.xml",
            "https://www.deepmind.com/blog/rss.xml",
        ]
    },
    {
        "name": "科技巨头与算力",
        "sources": [
            "https://stratechery.com/feed/",
        ]
    },
    {
        "name": "风险投资与商业趋势",
        "sources": [
            "http://www.paulgraham.com/rss.html",
            "https://a16z.com/feed/",
        ]
    },
    {
        "name": "宏观经济与货币周期",
        "sources": [
            "https://www.oaktreesurplus.com/insights/feed"
        ]
    },
    {
        "name": "二级市场与资本博弈",
        "sources": [
            # 可根据需要补充财经大咖博客或机构研报 RSS
        ]
    }
]

def fetch_feed_items():
    """遍历所有赛道信源，抓取最近更新"""
    raw_data = []
    for track in TRACKS:
        track_name = track["name"]
        for url in track["sources"]:
            try:
                feed = feedparser.parse(url)
                # 取每个源最近的 3 篇文章摘要
                for entry in feed.entries[:3]:
                    raw_data.append({
                        "track": track_name,
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", entry.get("description", ""))[:1500],
                        "link": entry.get("link", "")
                    })
            except Exception as e:
                print(f"抓取失败 [{url}]: {e}")
    return raw_data

def evaluate_and_summarize(items):
    """利用 Gemini 3.8 Flash 进行严苛打分筛选与极简提炼"""
    if not items:
        return "今日核心圈层无重磅输出。保持噪音过滤。"

    prompt = f"""
以下是一批过去 24 小时抓取自全球顶级科技领袖、投资人和思想家的公开发表内容（含标题与摘要）：

{items}

请执行以下任务：
1. 逐条评估其信息增量、反常识深度以及战略价值（满分 10 分）。剔除所有公关废话、日常寒暄和无实质内容的文章。
2. 每个赛道【最多选出 1 条】得分最高且超过 7.0 分的重磅内容。
3. 如果某赛道当天没有超过 7.0 分的干货，则该赛道轮空，不要强行凑数。
4. 语言必须极其精炼、惜字如金（绝不废话）。

请按以下固定格式输出飞书文本卡片内容：
【今日高管董事会】
- [赛道名称] 说话人/主题
  - 核心：1句话硬核结论
  - 价值：评分与入选理由（例如：9.0/10，直接改变大模型训练范式）

如果所有赛道今天集体哑火、没有 7 分以上内容，请直接统一输出："今日核心圈层无重磅输出。保持噪音过滤。"
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="你是一个极度严苛、追求高信噪比的首席科技与宏观资本分析师，行文惜字如金。严禁在输出中打印任何 API 密钥。",
            temperature=0.1,
        )
    )
    return response.text

def push_to_feishu(text):
    """通过 Webhook 发送到飞书机器人（注意：切勿在日志中明文打印 Webhook 或 Key）"""
    if not FEISHU_WEBHOOK:
        print("未配置飞书 Webhook 环境变量")
        return
    
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    res = requests.post(FEISHU_WEBHOOK, json=payload)
    print(f"飞书推送状态码: {res.status_code}")

if __name__ == "__main__":
    print("开始执行 5 人理论多赛道信源抓取...")
    items = fetch_feed_items()
    print(f"共抓取到原始条目数: {len(items)}")
    
    result_text = evaluate_and_summarize(items)
    print("生成摘要完成，正在推送到飞书...")
    push_to_feishu(result_text)
