# 🤖 AI Research Assistant Agent

> 一个具备**任务规划 + 自主搜索 + 对话记忆**的 AI 研究助手，支持终端和 Web 两种交互方式。

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58-FF4B4B)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🎯 项目亮点

- **三段式 Agent 架构**：规划（Plan） → 执行（Execute） → 汇总（Compile）
- **多轮 Function Calling**：LLM 自主决定搜索时机和关键词
- **并行搜索加速**：多子问题同时检索，速度提升 3~5 倍
- **上下文对话记忆**：支持追问、总结，会话可持久化
- **终端 + Web 双界面**：命令行调试 + Streamlit 可视化

---

## 🧠 Agent 工作流

```
用户输入话题
    │
    ▼
┌─────────────────┐
│  意图识别        │  ← 新话题？追问？总结？
└────────┬────────┘
         │
    ┌────▼────┐
    │ 制定计划  │  ← LLM 拆解为 3~5 个子问题
    └────┬────┘
         │
    ┌────▼──────────┐
    │ 并行搜索       │  ← 多线程 Function Calling + DuckDuckGo
    └────┬──────────┘
         │
    ┌────▼────┐
    │ 生成报告  │  ← 整合所有搜索结果，Markdown 输出
    └────┬────┘
         │
    ┌────▼────┐
    │ 保存记忆  │  ← 支持追问、会话持久化
    └─────────┘
```

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/Kong-tian/ai-research-assistant.git
cd ai-research-assistant
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置 API Key
```bash
copy .env.example .env
```
编辑 `.env`，填入你的 API Key（支持 OpenAI / DeepSeek / 任意兼容接口）：
```
API_KEY=sk-xxxxxxxxxxxxxxxx
API_BASE=https://api.deepseek.com    # 推荐 DeepSeek，便宜够用
MODEL_NAME=deepseek-chat
```

### 4. 运行

**终端版：**
```bash
python agent.py
```

**Web 版（推荐）：**
```bash
python -m streamlit run app.py
# 或双击 start.bat
```
浏览器打开 http://localhost:8501

---

## 📂 项目结构

```
ai-research-assistant/
├── agent.py            # 终端版入口（v3.0 完整功能）
├── app.py              # Streamlit Web 界面
├── agent_v1.py         # Step 1: 单轮搜索版（学习参考）
├── agent_v2.py         # Step 2: 规划+并行版（学习参考）
├── requirements.txt    # Python 依赖
├── .env.example        # 配置模板
├── .env                # 你的密钥（已 gitignore）
├── start.bat           # Windows 一键启动
├── data/               # 自动保存的研究报告
└── README.md
```

---

## 🏗️ 架构设计

### 核心模块

| 模块 | 职责 | 关键技术 |
|------|------|----------|
| `generate_plan()` | 任务分解 | LLM + JSON 结构化输出 |
| `detect_intent()` | 意图识别 | 对话上下文分析 |
| `parallel_search()` | 并行检索 | ThreadPoolExecutor + Function Calling |
| `ConversationMemory` | 对话记忆 | 历史管理 + 持久化 |
| `compile_report()` | 报告生成 | Markdown 格式化输出 |

### Agent 三要素

| 要素 | 实现 |
|------|------|
| 🧠 感知 (Perception) | 意图识别，区分新话题与追问 |
| 📋 规划 (Planning) | LLM 自动拆解复杂问题为子任务 |
| 🔧 行动 (Action) | Function Calling 驱动 DuckDuckGo 搜索 |

---

## 🔧 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| LLM | DeepSeek / OpenAI 兼容接口 | 可切换任意服务商 |
| 搜索 | DDGS（DuckDuckGo） | 免费，无需 API Key |
| Web 框架 | Streamlit | 纯 Python，快速构建 UI |
| 并发 | concurrent.futures | 并行搜索加速 |
| 配置 | python-dotenv | 环境变量管理 |

---

## 📸 效果演示

**Web 界面：**
- 左侧栏：对话历史，支持清空
- 主区域：输入话题 → 显示计划 → 进度条 → 完整报告
- 支持追问：Agent 自动结合上下文深入搜索

---

## 📈 迭代历程

| 版本 | 里程碑 |
|------|--------|
| v1.0 | 单轮搜索 + 报告生成 （130 行） |
| v2.0 | 任务规划 + 并行搜索 |
| v3.0 | 对话记忆 + 追问 + 会话持久化 |
| v4.0 | Streamlit Web 界面 |

---

## 🙋 FAQ

**Q: 跟 ChatGPT 有什么区别？**
A: ChatGPT 只能"聊"，这个 Agent 能自动搜网页、拆任务、逐步执行。它是真正的 Agent，不是 chatbot。

**Q: 支持哪些 LLM？**
A: 所有 OpenAI 兼容接口都支持（DeepSeek、GLM、Qwen、SiliconFlow 等），改 `.env` 即可。

**Q: 搜索不到结果？**
A: DuckDuckGo 在国内可能不稳定，可换成 Tavily Search API。或切换至全局代理。

---

## 📄 License

MIT © 2026