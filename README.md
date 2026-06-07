# AI 求职助手

基于阿里云 DashScope（通义千问）的多智能体 AI 求职助手。

上传简历 PDF + 职位描述，自动完成 ATS 评分、简历优化、面试题生成，中文输出结构化分析报告。支持历史记录、分享链接、进度追踪。

## 技术栈

| 层 | 技术 |
|---|---|
| LLM | 阿里云 DashScope — qwen-turbo / qwen-plus（三级模型分配） |
| LLM 封装 | LangChain（ChatPromptTemplate + BaseChatModel + LCEL） |
| 编排 | LangGraph 状态图工作流（两层并行执行） |
| 后端 | Python 3.11+ / FastAPI / Pydantic / SQLite |
| 前端 | Next.js 15 (App Router) / TailwindCSS / React 19 |
| PDF | PyMuPDF |
| 浏览器 | Playwright（JS 渲染页面抓取，可选） |

## 项目结构

```
AI_Job_Copilot/
├── backend/
│   ├── agents/               # 5 个 Agent（全部 LangChain 封装）
│   │   ├── llm.py             #   DashScopeChatModel（LangChain BaseChatModel）
│   │   ├── resume_parser.py  #   简历解析（PDF → 结构化 JSON，qwen-turbo）
│   │   ├── jd_analyzer.py    #   职位分析（JD → 关键词/技能/级别，qwen-turbo）
│   │   ├── ats_scorer.py     #   ATS 评分（0-100 + 四维拆解，qwen-plus）
│   │   ├── rewrite_agent.py  #   简历改写（ATS 关键词优化，qwen-plus）
│   │   └── interview_agent.py#   面试题生成（行为/技术/情景/缺口，qwen-plus）
│   ├── workflows/
│   │   ├── state.py          #   PipelineState（支持并行写入）
│   │   ├── graph.py          #   LangGraph DAG（两层并行）
│   │   └── progress.py       #   进度追踪（后台线程 + 前端轮询）
│   ├── schemas/              #   Pydantic 数据模型（6 组，全部中文输出）
│   ├── tools/                #   PDF 解析 + JD 抓取（4 层策略链）
│   ├── api/
│   │   ├── main.py           #   FastAPI 应用（分析 + 历史 + 进度）
│   │   └── debug_routes.py   #   调试端点（5 端点，逐个测试 Agent）
│   └── core/                 #   配置加载 + 日志 + SQLite 持久化
├── frontend/
│   └── src/
│       ├── app/page.tsx      #   主页面（上传 + 进度 + 结果 + 历史，中文 UI）
│       ├── components/       #   UI 组件（评分盘、技能标签、改写卡）
│       └── lib/              #   API 客户端 + 类型定义
├── tests/                    #   5 个阶段测试脚本
├── run.py                    #   后端启动入口
├── pyproject.toml
├── README.md
└── PROJECT_REFERENCE.md      #   详细函数级参考文档
```

## 工作流

两层并行执行，总耗时约 1 分钟：

```
              START
              ┌───┴───┐
              ↓       ↓
        parse_resume  analyze_jd     ← L1 并行（qwen-turbo + qwen-turbo）
              └───┬───┘
                  ↓
              score_ats              ← qwen-plus
              ┌───┴───┐
              ↓       ↓
           rewrite  interview        ← L2 并行（qwen-plus + qwen-plus）
              └───┬───┘
                  ↓
          aggregate_report
                  ↓
                 END
```

## 快速开始

### 1. 环境变量

```env
DASHSCOPE_API_KEY=sk-your-key-here
MODEL_NAME=qwen-plus
MODEL_NAME_SIMPLE=qwen-turbo
MODEL_NAME_COMPLEX=qwen-plus
```

### 2. 后端

```bash
uv sync
python run.py --port 8000
# API 文档: http://localhost:8000/docs
```

### 3. 前端

```bash
cd frontend && npm install && npm run dev -- --port 3001
# 访问: http://localhost:3001
```

### 4. 安装 Playwright（可选）

```bash
uv add playwright
playwright install chromium
```

不装也能用，JS 渲染网站的链接需要手动粘贴 JD 文本。

### 5. 测试

```bash
uv run python tests/test_phase1.py              # 配置 + DashScope 连通
uv run python tests/test_phase2.py              # JD 分析 + ATS 评分
uv run python tests/test_phase3.py              # 简历改写 + 面试题
uv run python tests/test_phase4.py              # 全流程 LangGraph
uv run python tests/test_phase5.py              # FastAPI 端点
```

## API 端点

### 分析流程

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/analyze` | 上传 PDF + JD，返回 session_id |
| GET | `/progress/{id}` | 轮询分析进度（5 步） |
| GET | `/result/{id}` | 获取分析结果 |

### 历史记录

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/history` | 列出所有历史记录 |
| GET | `/history/{id}` | 获取单次分析完整结果 |
| DELETE | `/history/{id}` | 删除记录 |

### 调试端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/debug/parse-resume` | 仅 PDF → 简历 JSON |
| POST | `/debug/analyze-jd` | 仅 JD 文本/URL → JD JSON |
| POST | `/debug/score-ats` | PDF + JD → ATS 评分 |
| POST | `/debug/rewrite` | PDF + JD → 简历改写 |
| POST | `/debug/interview` | PDF + JD → 面试题 |

## Agent 详情

| Agent | 主力模型 | 重试模型 | 输入 | 输出 |
|---|---|---|---|---|
| Resume Parser | qwen-turbo | qwen-plus | PDF 文本 | 技能/经历/项目/学历 JSON |
| JD Analyzer | qwen-turbo | qwen-plus | JD 文本/URL | 必备技能/加分技能/关键词/级别 |
| ATS Scorer | qwen-plus | qwen-plus | 简历 JSON + JD JSON | 0-100 分 + 四维拆解 + 匹配/缺失技能 |
| Rewrite Agent | qwen-plus | qwen-plus | 简历 + JD + ATS | 优化 bullet + 技能缺口计划 |
| Interview Agent | qwen-plus | qwen-plus | 简历 + JD + ATS | 行为/技术/情景/缺口面试题 |

每个 Agent 均使用 **LangChain LCEL 模式**：

```python
model = DashScopeChatModel(model="qwen-plus")
chain = ChatPromptTemplate.from_template(EXTRACTION_PROMPT) | model | StrOutputParser()
raw_output = chain.invoke({"resume_text": text})
```

- `DashScopeChatModel` — 继承 `BaseChatModel`，将 DashScope API 封装为 LangChain 原生模型
- JSON 解析失败自动重试（最多 2 次，用更强模型修复）
- 结构化日志（`@log_agent_execution` 装饰器，记录耗时和状态）
- Pydantic 输出强校验（`None` 自动兜底为空字符串）
- 全部中文输出（技能名保留原文）

## JD 链接抓取策略

按优先级依次尝试：

1. `<script>` 标签内嵌数据提取（JSON-LD / SPA 状态变量）
2. HTML 纯文本提取
3. Playwright 无头浏览器渲染
4. 返回中文错误提示，建议手动粘贴 JD 文本

## 主要特性

- **进度追踪**：后台管道执行，前端每 1.5s 轮询进度，5 步逐一亮对勾
- **历史记录**：SQLite 持久化所有分析结果，支持查看和删除
- **分享链接**：一键复制分享链接，他人打开直接查看分析结果
- **完整展示**：改写建议和面试题全部展示，分类 Tab 切换，支持展开/折叠
- **两层并行**：L1（简历+JD）和 L2（改写+面试）并行执行，总耗时约 1 分钟
- **模型分级**：turbo → simple，plus → complex，按任务复杂度分配

## 优化历程

| 版本 | 改动 | 耗时 |
|---|---|---|
| v1.0 | 串行 + qwen-max | ~211s |
| v1.1 | L2 并行（rewrite + interview） | ~140s |
| v1.2 | L1 并行 + 模型分级（turbo / plus） | **~67s** |

## 设计原则

- **模块化**：每个 Agent 可独立测试、独立部署
- **可观测**：每个节点独立计时、独立日志，调试端点逐级排查
- **容错**：任意节点失败 → 跳过后续 → 返回已有结果 + 错误阶段
- **安全**：所有密钥从 `.env` 读取，零硬编码
- **确定性**：Pydantic 强校验 + 字段级 `None` 兜底 + JSON 修复重试
- **中文优先**：LLM 输出、前端 UI、错误提示全部中文
