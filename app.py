"""
AI 研究助手 — Web 界面
启动方式: streamlit run app.py
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("API_KEY", "sk-your-key-here")
API_BASE = os.getenv("API_BASE", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "搜索互联网获取信息。",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "搜索关键词"}},
            "required": ["query"],
        },
    },
}]

DATA_DIR = Path("data")
CONV_DIR = DATA_DIR / "conversations"

# ---------- 搜索 ----------
def search_web(query: str, max_results: int = 5) -> list[dict]:
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return [
                {"title": r["title"], "body": r["body"], "href": r["href"]}
                for r in ddgs.text(query, max_results=max_results)
            ]
    except ImportError:
        return [{"title": "搜索模块未安装", "body": "pip install ddgs", "href": ""}]

# ---------- 计划 ----------
def generate_plan(topic: str) -> list[str]:
    now = datetime.now()
    today = now.strftime("%Y年%m月%d日")
    wd = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"][now.weekday()]
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{
            "role": "system",
            "content": f"今天是{today} {wd}。把话题拆成3~5个子问题。只输出JSON数组：['问题1','问题2']",
        }, {"role": "user", "content": f"制定计划：{topic}"}],
        temperature=0.3,
    )
    raw = resp.choices[0].message.content or "[]"
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        plan = json.loads(raw)
        if isinstance(plan, list) and plan:
            return plan
    except json.JSONDecodeError:
        pass
    return [topic]

# ---------- 单问题搜索 ----------
def research_one(question: str) -> list[dict]:
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "搜索助手。调用search_web搜索。"},
            {"role": "user", "content": f"搜索：{question}"},
        ],
        tools=TOOLS, tool_choice="auto",
    )
    msg = resp.choices[0].message
    if msg.tool_calls:
        for tc in msg.tool_calls:
            if tc.function.name == "search_web":
                args = json.loads(tc.function.arguments)
                return search_web(args["query"])
    return []

# ---------- 并行搜索 ----------
def parallel_search(plan: list[str], progress_bar, status_text) -> dict:
    findings = {}
    total = len(plan)
    done = 0
    with ThreadPoolExecutor(max_workers=min(total, 5)) as ex:
        futures = {ex.submit(research_one, q): q for q in plan}
        for f in as_completed(futures):
            q = futures[f]
            try:
                findings[q] = f.result()
            except Exception as e:
                findings[q] = []
            done += 1
            progress_bar.progress(done / total)
            status_text.text(f"已完成 {done}/{total}: {q}")
    return findings

# ---------- 报告 ----------
def make_report(topic: str, plan: list[str], findings: dict, context: str = "") -> str:
    ctx = f"\n上文背景：{context}" if context else ""
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{
            "role": "system",
            "content": "专业研究报告撰写者。Markdown格式。基于搜索结果，不编造。",
        }, {
            "role": "user",
            "content": f"话题：{topic}{ctx}\n计划：{json.dumps(plan, ensure_ascii=False)}\n结果：{json.dumps(findings, ensure_ascii=False, indent=2)}\n生成报告。",
        }],
    )
    return resp.choices[0].message.content or "生成失败。"

# ---------- 意图判断 ----------
def detect_intent(user_input: str, history: str) -> str:
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{
            "role": "system",
            "content": '判断用户输入是"new"(新话题)还是"follow"(追问上文)。只输出一个词。',
        }, {"role": "user", "content": f"历史：\n{history}\n\n用户输入：{user_input}"}],
        temperature=0.1,
    )
    result = (resp.choices[0].message.content or "new").strip().lower()
    return "follow" if "follow" in result else "new"

# ---------- UI ----------
st.set_page_config(page_title="AI 研究助手", page_icon="🤖", layout="wide")
st.title("🤖 AI 研究助手")
st.caption("输入研究话题，自动搜索、分析、生成报告")

# 侧边栏
with st.sidebar:
    st.header("📋 对话历史")
    if "history" not in st.session_state:
        st.session_state.history = []
        st.session_state.last_topic = ""
        st.session_state.last_report = ""

    if st.session_state.history:
        for i, h in enumerate(st.session_state.history):
            with st.expander(f"{'🧑' if h['role']=='user' else '🤖'} {h['content'][:60]}...", expanded=False):
                st.write(h["content"])

    if st.button("🗑️ 清空历史"):
        st.session_state.history = []
        st.session_state.last_topic = ""
        st.session_state.last_report = ""
        st.rerun()

# 主区域
user_input = st.chat_input("输入研究话题...")

if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("分析中..."):
            try:
                # 判断意图
                history_text = "\n".join(
                    f"[{'用户' if h['role']=='user' else 'Agent'}]: {h['content'][:200]}"
                    for h in st.session_state.history[-6:]
                )

                if user_input.strip() in ("总结", "汇总"):
                    st.info("📋 生成对话总结...")
                    conv = json.dumps(st.session_state.history, ensure_ascii=False)
                    resp = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "system", "content": "总结研究对话，Markdown格式。"},
                                  {"role": "user", "content": f"对话：{conv}\n总结。"}],
                    )
                    report = resp.choices[0].message.content or ""

                elif st.session_state.last_topic and detect_intent(user_input, history_text) == "follow":
                    st.info(f"💡 追问模式，结合上文...")
                    plan = [user_input]
                    progress = st.progress(0)
                    status = st.empty()
                    findings = parallel_search(plan, progress, status)
                    report = make_report(user_input, plan, findings, st.session_state.last_report[:500])

                else:
                    st.session_state.last_topic = user_input
                    st.info("🧠 生成研究计划...")
                    plan = generate_plan(user_input)
                    st.write("**研究计划：**")
                    for i, q in enumerate(plan, 1):
                        st.write(f"{i}. {q}")

                    st.info(f"🔎 并行搜索 {len(plan)} 个子问题...")
                    progress = st.progress(0)
                    status = st.empty()
                    findings = parallel_search(plan, progress, status)

                    st.info("📝 生成报告...")
                    report = make_report(user_input, plan, findings)

                st.session_state.last_report = report
                st.session_state.history.append({"role": "agent", "content": report})
                st.markdown(report)

                # 保存
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe = "".join(c if c.isalnum() else "_" for c in user_input)[:20]
                fname = DATA_DIR / f"report_{safe}_{ts}.md"
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(f"# {user_input}\n\n*{datetime.now():%Y-%m-%d %H:%M:%S}*\n\n{report}")
                st.caption(f"💾 已保存: {fname}")

            except Exception as e:
                st.error(f"出错了: {e}")
                st.info("请检查 .env 中的 API_KEY。")