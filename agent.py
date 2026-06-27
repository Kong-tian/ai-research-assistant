"""
AI 研究助手 Agent —— Step 3 对话记忆版
=========================================
新能力：记住上下文、支持追问、会话可保存

对话示例：
  你: 量子计算有哪些应用？
  Agent: [搜完，生成报告...]

  你: 那金融领域具体有哪些公司在做？   ← Agent 知道你在追问量子计算
  Agent: [结合上文，搜"量子计算 金融 公司"...]

  你: 总结一下                    ← Agent 汇总整段对话的研究成果
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

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

# --------------- 数据目录 ---------------
DATA_DIR = Path("data")
CONV_DIR = DATA_DIR / "conversations"


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


# --------------- 对话记忆 ---------------
class ConversationMemory:
    """管理对话历史，支持保存和加载"""

    def __init__(self):
        self.history: list[dict] = []   # {"role": "user"|"agent", "content": "...", "time": "..."}
        self.last_topic: str = ""        # 最近一个研究话题
        self.topic_context: str = ""     # 当前话题的上下文摘要

    def add_user(self, text: str):
        self.history.append({"role": "user", "content": text, "time": _now()})

    def add_agent(self, text: str):
        self.history.append({"role": "agent", "content": text, "time": _now()})

    def get_recent(self, n: int = 6) -> str:
        """获取最近 n 条对话，用于判断意图"""
        lines = []
        for h in self.history[-n:]:
            role = "用户" if h["role"] == "user" else "Agent"
            lines.append(f"[{role}] {h['content'][:200]}")
        return "\n".join(lines)

    def save(self, name: str = ""):
        CONV_DIR.mkdir(parents=True, exist_ok=True)
        filename = CONV_DIR / f"{name or _now('file')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "last_topic": self.last_topic,
                "topic_context": self.topic_context,
                "history": self.history,
            }, f, ensure_ascii=False, indent=2)
        return filename

    def load(self, filename: str):
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.last_topic = data.get("last_topic", "")
        self.topic_context = data.get("topic_context", "")
        self.history = data.get("history", [])


# --------------- 意图判断 ---------------
def detect_intent(user_input: str, memory: ConversationMemory) -> tuple[str, str]:
    """
    返回 (意图类型, 提炼后的查询)
    意图类型: "new_topic" | "follow_up" | "summarize"
    """
    # 明确指令
    lower = user_input.strip().lower()
    if lower in ("总结", "汇总", "总结一下", "帮我总结", "summary"):
        return ("summarize", "")

    # 没有上文 = 新话题
    if not memory.last_topic:
        return ("new_topic", user_input)

    # 问 LLM：这是新话题还是追问？
    recent = memory.get_recent()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个对话分析器。判断用户最后一条消息是：\n"
                    "- new: 开启了全新的话题（和上文无关）\n"
                    "- follow: 在上一个话题基础上的追问或深入\n\n"
                    "只输出一个 JSON："
                    '{"intent": "new"|"follow", "refined_query": "提炼后的搜索查询"}\n'
                    "如果是 follow，refined_query 要结合上文补全隐含信息（如代词、省略）。"
                ),
            },
            {"role": "user", "content": f"对话历史：\n{recent}\n\n用户最新输入：{user_input}"},
        ],
        temperature=0.1,
    )

    raw = response.choices[0].message.content or "{}"
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(raw)
        intent = result.get("intent", "new")
        refined = result.get("refined_query", user_input)
        if intent == "follow":
            return ("follow_up", refined)
    except json.JSONDecodeError:
        pass

    return ("new_topic", user_input)


# --------------- 计划生成 ---------------
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
                    "你是一个研究规划师。把话题拆成 3~5 个具体子问题。\n"
                    '只输出 JSON 数组：["子问题1", "子问题2"]'
                ),
            },
            {"role": "user", "content": f"制定研究计划：{topic}"},
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


# --------------- 单问题搜索 ---------------
def research_sub_question(question: str) -> list[dict]:
    messages: list[dict] = [
        {"role": "system", "content": "搜索助手。调用 search_web 搜索后返回结果。"},
        {"role": "user", "content": f"搜索：{question}"},
    ]

    response = client.chat.completions.create(
        model=MODEL_NAME, messages=messages, tools=TOOLS, tool_choice="auto"
    )
    msg = response.choices[0].message

    if not msg.tool_calls:
        return []

    for tc in msg.tool_calls:
        if tc.function.name == "search_web":
            args = json.loads(tc.function.arguments)
            return search_web(args["query"])

    return []


# --------------- 并行搜索 ---------------
def execute_plan(plan: list[str]) -> dict[str, list[dict]]:
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
                print(f"   [{i}/{total}] ✅ {question} → {len(results)} 条")
            except Exception as e:
                findings[question] = []
                print(f"   [{i}/{total}] ❌ {question} → {e}")

    return findings


# --------------- 生成报告 ---------------
def compile_report(topic: str, plan: list[str], findings: dict[str, list[dict]],
                   context: str = "") -> str:
    findings_json = json.dumps(findings, ensure_ascii=False, indent=2)
    context_block = f"\n\n上文背景：{context}" if context else ""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "专业研究报告撰写者。Markdown 格式。"
                    "包含概述、各维度分析、关键发现、参考链接。"
                    "基于搜索结果，不编造。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"话题：{topic}{context_block}\n\n"
                    f"研究计划：{json.dumps(plan, ensure_ascii=False)}\n\n"
                    f"搜索结果：{findings_json}\n\n"
                    "生成报告。"
                ),
            },
        ],
    )
    return response.choices[0].message.content or "无法生成报告。"


# --------------- 汇总整段对话 ---------------
def summarize_conversation(memory: ConversationMemory) -> str:
    history_json = json.dumps(memory.history, ensure_ascii=False, indent=2)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "总结整段研究对话，Markdown 格式。列出所有讨论过的话题、核心发现、关键结论。",
            },
            {"role": "user", "content": f"对话历史：\n{history_json}\n\n请总结。"},
        ],
    )
    return response.choices[0].message.content or "总结失败。"


# --------------- 工具函数 ---------------
def _now(fmt: str = "time") -> str:
    now = datetime.now()
    if fmt == "time":
        return now.strftime("%H:%M")
    return now.strftime("%Y%m%d_%H%M%S")


def print_banner():
    os.system("cls" if os.name == "nt" else "clear")
    print()
    print("╔══════════════════════════════════════════╗")
    print("║     🤖 AI 研究助手 Agent v3.0          ║")
    print("║     Step 3 — 对话记忆 + 追问           ║")
    print("╚══════════════════════════════════════════╝")
    print("  命令: /save 保存  /load 加载  /history 历史  q 退出")
    print()


# --------------- 主入口 ---------------
if __name__ == "__main__":
    print_banner()
    memory = ConversationMemory()

    while True:
        print()
        try:
            user_input = input("🎯 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "q":
            print("👋 再见！")
            break

        # ---- 命令处理 ----
        if user_input.startswith("/save"):
            name = user_input[5:].strip()
            path = memory.save(name)
            print(f"💾 对话已保存至: {path}")
            continue

        if user_input.startswith("/load"):
            path = user_input[5:].strip()
            if path:
                memory.load(path)
                print(f"📂 已加载对话: {path}")
                print(f"   话题: {memory.last_topic}")
                print(f"   共 {len(memory.history)} 条消息")
            else:
                # 列出可加载的文件
                if CONV_DIR.exists():
                    files = list(CONV_DIR.glob("*.json"))
                    if files:
                        print("可加载的对话：")
                        for f in files:
                            print(f"   /load {f}")
                    else:
                        print("没有已保存的对话。")
                else:
                    print("没有已保存的对话。")
            continue

        if user_input.lower() in ("/history", "/历史"):
            if not memory.history:
                print("暂无对话历史。")
            else:
                for h in memory.history:
                    role = "🧑" if h["role"] == "user" else "🤖"
                    print(f"[{h['time']}] {role} {h['content'][:100]}...")
            continue

        # ---- 意图判断 ----
        memory.add_user(user_input)
        intent, query = detect_intent(user_input, memory)

        try:
            if intent == "summarize":
                print("\n📋 正在总结全部对话...")
                summary = summarize_conversation(memory)
                memory.add_agent(summary)
                print(f"\n{summary}")

            elif intent == "follow_up":
                print(f"\n💡 检测到追问，结合上文搜索: {query}")
                plan = [query]  # 追问只搜一个方向
                findings = execute_plan(plan)
                report = compile_report(query, plan, findings, memory.topic_context)
                memory.add_agent(report)
                print(f"\n{report}")

            else:  # new_topic
                memory.last_topic = query
                print(f"\n🔬 新话题: {query}")

                print("🧠 生成研究计划...")
                plan = generate_plan(query)
                for i, q in enumerate(plan, 1):
                    print(f"   {i}. {q}")

                print(f"\n🔎 并行搜索...")
                findings = execute_plan(plan)

                print(f"\n📝 生成报告...")
                report = compile_report(query, plan, findings)
                memory.add_agent(report)
                memory.topic_context = report[:500]  # 截取前 500 字作为上下文

                print(f"\n{report}")

            # 自动保存
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_" for c in query)[:20]
            filename = DATA_DIR / f"report_{safe_name}_{timestamp}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# {query}\n\n*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                last = memory.history[-1]["content"] if memory.history else ""
                f.write(last)
            print(f"\n💾 已保存: {filename}")

        except Exception as e:
            print(f"\n❌ 出错了: {e}")