import os
import sys
import requests
import feedparser
from google import genai
from google.genai import types

# 1. 检查环境变量
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")

if not GEMINI_API_KEY:
    print("错误: 未检测到 GEMINI_API_KEY 密钥，请检查 GitHub Secrets 设置。")
    sys.exit(1)

# 初始化 Gemini 客户端
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"初始化 Gemini 客户端失败: {e}")
    sys.exit(1)

# 5大核心领域赛道及稳定信源
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
        ]
    },
    {
        "name": "宏观经济与货币周期",
        "sources": [
            # 如有稳定的宏观 RSS 可在此添加
        ]
    }
]

def fetch_feed_items():
    """带独立容错的 RSS 抓取逻辑"""
    raw_data = []
    for track in TRACKS:
        track_name = track["name"]
        for url in track["sources"]:
            try:
                print(f"正在抓取 [{track_name}] -> {url}")
                response = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code != 200:
                    print(f"  -> 状态码异常 [{response.status_code}]，跳过该源")
                    continue
                
                feed = feedparser.parse(response.content)
                entries = feed.entries[:3]
                print(f"  -> 成功获取 {len(entries)} 条内容")
                
                for entry in entries:
                    raw_data.append({
                        "track": track_name,
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", entry.get("description", ""))[:1500],
                        "link": entry.get("link", "")
                    })
            except Exception as e:
                print(f"  -> 抓取该源时发生异常（已安全跳过）: {e}")
    return raw_data

def evaluate_and_summarize(items):
    """利用 Gemini 3.8 Flash 进行严苛打分筛选"""
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

    try:
        print("正在调用 Gemini 3.8 Flash 模型进行分析与打分...")
        response = client.models.generate_content(
            model="gemini-3.8-flash",  # 修正为最新可用的 Flash 模型
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="你是一个极度严苛、追求高信噪比的首席科技与宏观资本分析师，行文惜字如金。",
                temperature=0.1,
            )
        )
        return response.text
    except Exception as e:
        print(f"Gemini API 调用报错: {e}")
        raise e  # 抛出异常，不再静默吞错

def push_to_feishu(text):
    """推送到飞书"""
    print("--- 准备推送到飞书的内容 ---")
    print(text)
    print("------------------------")

    if not FEISHU_WEBHOOK:
        print("提示: 未配置 FEISHU_WEBHOOK，跳过飞书推送。")
        return
    
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    try:
        res = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        print(f"飞书推送状态码: {res.status_code}, 响应: {res.text}")
    except Exception as e:
        print(f"飞书推送网络异常: {e}")

if __name__ == "__main__":
    print("脚本启动：开始执行多赛道信源抓取任务...")
    items = fetch_feed_items()
    print(f"总计聚合原始条目数: {len(items)}")
    
    result_text = evaluate_and_summarize(items)
    print("生成摘要完成，开始推送...")
    push_to_feishu(result_text)
    print("全部流程顺利结束！")
