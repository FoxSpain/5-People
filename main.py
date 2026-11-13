import os
import sys
import requests
import feedparser
from google import genai
from google.genai import types

# 环境变量初始化
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")

if not GEMINI_API_KEY:
    print("错误: 未检测到 GEMINI_API_KEY 环境变量")
    sys.exit(1)

# 初始化 Gemini 客户端
client = genai.Client(api_key=GEMINI_API_KEY)

# 5大核心领域赛道及代表性高质量信源
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
    }
]

def fetch_feed_items():
    """遍历所有赛道信源，带 5 秒超时保护，防止请求卡死"""
    raw_data = []
    for track in TRACKS:
        track_name = track["name"]
        for url in track["sources"]:
            try:
                print(f"正在抓取 [{track_name}] -> {url}")
                response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code != 200:
                    print(f"跳过: 状态码异常 [{response.status_code}]")
                    continue
                
                feed = feedparser.parse(response.content)
                entries = feed.entries[:3]
                print(f"成功获取 {len(entries)} 条内容")
                
                for entry in entries
