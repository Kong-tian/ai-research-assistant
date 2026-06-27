"""
AI 研究助手 Agent —— Step 1 最简版
=====================================
功能：用户给定一个研究话题，Agent 自动调用搜索引擎搜集资料，最后汇总成结构化报告。

核心技术点：
  - OpenAI 兼容 API 调用（支持 OpenAI / DeepSeek / 其他兼容服务）
  - Function Calling，支持多轮搜索
  - DuckDuckGo 免费搜索（ddgs 包）

使用方式：
  1. 复制 .env.example 为 .env，填入你的 API Key
  2. pip install -r requirements.txt
  3. python agent.py
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

# --------------- 加载配置 ---------------
load_dotenv()

API_KEY = os.getenv("API_KEY", "sk-your-key-here")
API_BASE = os.getenv("API_BASE", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

# --------------- 工具定义 ---------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "搜索互联网获取最新信息。需要查找实时数据、最新新闻或模型训练数据以外的知识时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

# --------------- 搜索实现 ---------------
def search_web(query: str, max_results: int = 5) -> list[dict]:
    """使用 DuckDuckGo 搜索（ddgs 包），返回标题+摘要+链接"""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r["title"],
                    "body": r["body"],
                    "href": r["href"],
                })
        return results
    except ImportError:
        return [{"title": "搜索模块未安装", "body": "pip install ddgs", "href": ""}]


# --------------- Agent 核心循环 ---------------
def research(topic: str, max_rounds: int = 3) -> str:
    """给定研究主题，返回结构化的研究报告。"""

    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日 %H:%M")
    weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]

    print(f"\n{'='*60}")
    print(f"\U0001f50d 研究主题: {topic}")
    print(f"{'='*60}\n")

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个专业的研究助手。\n\n"
                f"【当前时间】{today_str} {weekday}\n\n"
                "工作流程：\n"
                "1. 先调用 search_web 搜索相关资料\n"
                "2. 如果搜索结果不够充分，可以再次搜索\n"
                "3. 资料收集足够后，整合成一份结构化报告\n\n"
                "报告应包含：概述、关键发现、数据支撑、参考文献链接。\n"
                "使用 Markdown 格式输出。\n\n"
                "⚠️ 重要规则：\n"
                "- 搜索实时信息（天气、股价、新闻等）时，必须在搜索关键词中包含当前日期\n"
                "- 不要凭空编造，一切以搜索结果为准\n"
                "- 注意信息的时效性，优先使用最新的资料"
            ),
        },
        {
            "role": "user",
            "content": f"请帮我研究：{topic}",
        },
    ]

    # ---------- 多轮循环 ----------
    for round_num in range(1, max_rounds + 2):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message

        if not assistant_message.tool_calls:
            return assistant_message.content or "无法生成报告。"

        print(f"\U0001f9e0 [第{round_num}轮] Agent 想要搜索...\n")
        messages.append(assistant_message)

        for tool_call in assistant_message.tool_calls:
            if tool_call.function.name == "search_web":
                args = json.loads(tool_call.function.arguments)
                query = args["query"]
                print(f"   \U0001f50e 搜索: {query}")

                results = search_web(query)
                print(f"      → 找到 {len(results)} 条结果")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(results, ensure_ascii=False),
                })

        print()

    print("\U0001f4dd 达到最大搜索轮数，强制生成报告...\n")
    messages.append({
        "role": "user",
        "content": "请基于以上搜索结果生成完整报告，不要再搜索了。",
    })
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
    )
    return response.choices[0].message.content or "无法生成报告。"


# --------------- 主入口 ---------------
if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")

    print("\n╔══════════════════════════════════════════╗")
    print("║     🤖 AI 研究助手 Agent v1.0          ║")
    print("║     Step 1 — 多轮搜索 + 报告生成       ║")
    print("╚══════════════════════════════════════════╝")

    while True:
        print()
        topic = input("🎯 请输入研究话题 (输入 q 退出): ").strip()
        if topic.lower() == "q":
            print("👋 再见！")
            break
        if not topic:
            continue

        try:
            report = research(topic)
            print("\n" + "=" * 60)
            print("📄 研究报告")
            print("=" * 60)
            print(report)
            print("=" * 60)

            os.makedirs("data", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_" for c in topic)[:30]
            filename = f"data/report_{safe_name}_{timestamp}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# 研究报告：{topic}\n\n")
                f.write(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(report)
            print(f"\n💾 报告已保存至: {filename}")

        except Exception as e:
            print(f"\n❌ 出错了: {e}")
            print("请检查 .env 文件中的 API_KEY 和 API_BASE 是否正确。")
