"""
AI 研究助手 Agent —— Step 2 规划版（并行加速）
================================================
新能力：先拆任务 → 并行搜索所有子问题 → 最终汇总
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

# --------------- 配置 ---------------
load_dotenv()

API_KEY = os.getenv("API_KEY", "sk-your-key-here")
API_BASE = os.getenv("API_BASE", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "搜索互联网获取信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    }
]


# --------------- 搜索实现 ---------------
def search_web(query: str, max_results: int = 5) -> list[dict]:
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


# --------------- 单问题搜索（减为一轮，够用了） ---------------
def research_sub_question(question: str) -> list[dict]:
    """针对单个子问题搜索，只搜一轮"""
    messages: list[dict] = [
        {"role": "system", "content": "你是一个搜索助手。请调用 search_web 搜索相关资料后返回。"},
        {"role": "user", "content": f"请搜索：{question}"},
    ]

    response = client.chat.completions.create(
        model=MODEL_NAME, messages=messages, tools=TOOLS, tool_choice="auto"
    )
    msg = response.choices[0].message

    if not msg.tool_calls:
        return []

    results = []
    for tc in msg.tool_calls:
        if tc.function.name == "search_web":
            args = json.loads(tc.function.arguments)
            results = search_web(args["query"])

    return results


# --------------- 一阶段：生成研究计划 ---------------
def generate_plan(topic: str) -> list[str]:
    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日")
    weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    f"今天是{today_str} {weekday}。"
                    "你是一个研究规划师。用户给一个话题，你把它拆成 3~5 个具体的子问题。\n"
                    "每个子问题应该独立、可搜索、有明确的研究目标。\n\n"
                    "只输出一个 JSON 数组，格式如：\n"
                    '["子问题1", "子问题2", "子问题3"]\n\n'
                    "不要输出任何其他内容。"
                ),
            },
            {"role": "user", "content": f"请为以下话题制定研究计划：{topic}"},
        ],
        temperature=0.3,
    )

    raw = response.choices[0].message.content or "[]"
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        plan = json.loads(raw)
        if isinstance(plan, list) and len(plan) > 0:
            return plan
    except json.JSONDecodeError:
        pass
    return [topic]


# --------------- 二阶段：并行执行 ---------------
def execute_plan(plan: list[str]) -> dict[str, list[dict]]:
    """并行搜索所有子问题"""
    findings = {}
    total = len(plan)

    with ThreadPoolExecutor(max_workers=min(total, 5)) as executor:
        futures = {
            executor.submit(research_sub_question, q): (i, q)
            for i, q in enumerate(plan, 1)
        }

        for future in as_completed(futures):
            i, question = futures[future]
            try:
                results = future.result()
                findings[question] = results
                print(f"   [{i}/{total}] ✅ {question} → 找到 {len(results)} 条")
            except Exception as e:
                findings[question] = []
                print(f"   [{i}/{total}] ❌ {question} → {e}")

    return findings


# --------------- 三阶段：汇总报告 ---------------
def compile_report(topic: str, plan: list[str], findings: dict[str, list[dict]]) -> str:
    findings_json = json.dumps(findings, ensure_ascii=False, indent=2)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个专业的研究报告撰写者。"
                    "使用 Markdown 格式输出结构化研究报告。"
                    "包含：概述、各维度分析、关键发现、参考文献链接。"
                    "基于提供的搜索结果撰写，不要编造。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"话题：{topic}\n\n"
                    f"研究计划：{json.dumps(plan, ensure_ascii=False)}\n\n"
                    f"搜索结果：{findings_json}\n\n"
                    "请生成最终研究报告。"
                ),
            },
        ],
    )

    return response.choices[0].message.content or "无法生成报告。"


# --------------- 主流程 ---------------
def research(topic: str) -> str:
    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日 %H:%M")
    weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]

    print(f"\n{'='*60}")
    print(f"\U0001f52c 研究话题: {topic}")
    print(f"\U0001f4c5 {today_str} {weekday}")
    print(f"{'='*60}")

    print("\n\U0001f9e0 【阶段 1/3】生成研究计划...")
    plan = generate_plan(topic)
    print()
    for i, q in enumerate(plan, 1):
        print(f"   {i}. {q}")

    print(f"\n\U0001f50e 【阶段 2/3】并行搜索（共 {len(plan)} 项，同时进行）...")
    findings = execute_plan(plan)

    print(f"\n\U0001f4dd 【阶段 3/3】汇总生成报告...")
    report = compile_report(topic, plan, findings)

    return report


# --------------- 主入口 ---------------
if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")

    print()
    print("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
    print("\u2551     \U0001f916 AI \u7814\u7a76\u52a9\u624b Agent v2.1        \u2551")
    print("\u2551     Step 2 \u2014 \u5e76\u884c\u641c\u7d22\u52a0\u901f\u7248          \u2551")
    print("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d")

    while True:
        print()
        topic = input("\U0001f3af \u8bf7\u8f93\u5165\u7814\u7a76\u8bdd\u9898 (\u8f93\u5165 q \u9000\u51fa): ").strip()
        if topic.lower() == "q":
            print("\U0001f44b \u518d\u89c1\uff01")
            break
        if not topic:
            continue

        try:
            report = research(topic)
            print("\n" + "=" * 60)
            print("\U0001f4c4 \u6700\u7ec8\u7814\u7a76\u62a5\u544a")
            print("=" * 60)
            print(report)
            print("=" * 60)

            os.makedirs("data", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_" for c in topic)[:30]
            filename = f"data/report_{safe_name}_{timestamp}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# \u7814\u7a76\u62a5\u544a\uff1a{topic}\n\n")
                f.write(f"*\u751f\u6210\u65f6\u95f4\uff1a{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(report)
            print(f"\n\U0001f4be \u62a5\u544a\u5df2\u4fdd\u5b58\u81f3: {filename}")

        except Exception as e:
            print(f"\n\u274c \u51fa\u9519\u4e86: {e}")
            print("\u8bf7\u68c0\u67e5 .env \u6587\u4ef6\u4e2d\u7684 API_KEY \u548c API_BASE \u662f\u5426\u6b63\u786e\u3002")