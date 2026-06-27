# 🤖 AI 研究助手 Agent

一个基于大语言模型的 AI 研究助手，能自动搜索互联网资料并生成结构化研究报告。

适合 AI 开发入门练手，从最简版开始逐步进阶。**可以放进简历的项目。**

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API

```bash
# 复制配置模板
copy .env.example .env

# 编辑 .env，填入你的 API Key
# 支持 OpenAI、DeepSeek 或任何 OpenAI 兼容接口
```

`.env` 示例（DeepSeek，便宜适合练手）：

```
API_KEY=sk-xxxxxxxxxxxxxxxx
API_BASE=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

### 3. 运行

```bash
python agent.py
```

输入研究话题即可，比如：

```
🎯 请输入研究话题: 2026年AI Agent领域的最新进展
```

---

## 📂 项目结构

```
ai-research-assistant/
├── agent.py            # 主程序（Step 1 最简版）
├── requirements.txt    # Python 依赖
├── .env.example        # 配置模板（提交到Git）
├── .env                # 你自己的配置（不要提交）
├── data/               # 自动保存的研究报告
└── README.md           # 本文件
```

---

## 🧠 Step 1 做了什么（当前版本）

```
用户输入话题 → Agent 自动搜索 → 收集资料 → LLM 汇总 → 生成Markdown报告
```

核心代码不到 150 行，覆盖了：

| 能力 | 在哪里 |
|------|--------|
| OpenAI 兼容 API 调用 | `client.chat.completions.create()` |
| Function Calling（工具调用） | `TOOLS` 定义 + `tool_choice="auto"` |
| Web 搜索 | `search_web()` → DuckDuckGo |
| 报告生成 | LLM 根据搜索结果自动写 |
| 对话记忆 | `messages` 列表累积上下文 |

---

## 📈 进阶路线（自己扩展）

### Step 2：多步规划
- 引入 LangChain Agent 模块
- 让 Agent 把大任务拆成多个子步骤，一步步执行
- 比如"研究量子计算"→ 先搜概述→再搜金融应用→再搜挑战→汇总

### Step 3：长期记忆
- 用向量数据库（Chroma / FAISS）存储之前搜过的内容
- 避免重复搜索，支持追问和深入

### Step 4：加个界面
- 用 Streamlit 或 Gradio 打包成 Web 应用
- 让非程序员也能用

### Step 5：多 Agent 协作
- 一个 Agent 负责搜索，一个负责分析，一个负责写报告
- 用 CrewAI 或 AutoGen 框架

---

## 🔧 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | |
| LLM SDK | openai >= 1.0 | 兼容 OpenAI / DeepSeek 等 |
| 搜索 | duckduckgo-search | 免费，无需 API Key |
| 配置 | python-dotenv | .env 文件管理 |
| 向量存储（Step 3） | Chroma / FAISS | 轻量级，本地运行 |

---

## ❓ 常见问题

**Q: 为什么用 DuckDuckGo 而不是 Google？**
A: DuckDuckGo 免费且不需要 API Key，入门零成本。进阶后可以换成 Tavily 或 SerpAPI。

**Q: 搜索不到结果？**
A: 检查网络，DuckDuckGo 在国内可能不稳定。可以换成 Tavily Search API（有免费额度）。

**Q: 支持国内大模型吗？**
A: 只要提供 OpenAI 兼容接口的都支持，比如 DeepSeek、智谱 GLM、通义千问等。改 `.env` 里的 `API_BASE` 和 `MODEL_NAME` 即可。

---

## 📄 License

MIT — 随便用、随便改、随便放进简历。
