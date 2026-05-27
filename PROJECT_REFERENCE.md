# AI Job Copilot — 项目详细参考文档

## 项目概述

基于阿里云 DashScope（通义千问）的多智能体 AI 求职助手。上传简历 PDF + 职位描述，自动完成简历解析、JD 分析、ATS 评分、简历优化、面试题生成，输出结构化报告。

**核心架构**：Backend (Python/FastAPI/LangGraph) + Frontend (Next.js/TailwindCSS)

---

## 一、根目录文件

### `.env`

- `DASHSCOPE_API_KEY` — 阿里云 DashScope API 密钥（必填）
- `MODEL_NAME` — 通用任务模型，默认 `qwen-plus`
- `MODEL_NAME_SIMPLE` — 简单提取模型，默认 `qwen-turbo`
- `MODEL_NAME_COMPLEX` — 复杂推理模型，默认 `qwen-plus`
- `DASHSCOPE_BASE_URL` — API 地址
- `DB_PATH` — SQLite 数据库路径，默认项目根目录 `analyses.db`

### `pyproject.toml`

Python 项目配置文件。核心依赖：`dashscope`（LLM SDK）、`fastapi`（Web 框架）、`langgraph`（工作流编排）、`pydantic`（数据校验）、`PyMuPDF`（PDF 解析）、`httpx`（HTTP 客户端）、`playwright`（无头浏览器，可选）。

### `run.py`

后端启动入口脚本。

- `main()` — 解析命令行参数（`--host`、`--port`、`--reload`），检测端口占用，启动 uvicorn 服务器

用法：`python run.py --port 8000 --reload`

### `README.md`

项目简介、技术栈、快速开始、API 文档。

---

## 二、backend/core/ — 核心基础设施

### backend/core/config.py

全局配置管理，使用 `python-dotenv` 从 `.env` 加载所有环境变量。

**`class Settings`** — 配置类，所有字段从环境变量读取并有默认值：

- `Settings.DASHSCOPE_API_KEY` — DashScope API 密钥
- `Settings.MODEL_NAME` — 通用模型名，默认 `qwen-plus`
- `Settings.MODEL_NAME_SIMPLE` — 简单任务模型名，默认 `qwen-turbo`
- `Settings.MODEL_NAME_COMPLEX` — 复杂任务模型名，默认 `qwen-plus`
- `Settings.EMBEDDING_MODEL` — 嵌入模型名
- `Settings.LANGSMITH_API_KEY` / `LANGSMITH_TRACING` / `LANGSMITH_PROJECT` — LangSmith 追踪配置（可选）
- `Settings.TEMP_DIR` — 临时文件目录
- `Settings.validate()` — 校验必需的环境变量是否已设置，未设置则抛出 `ValueError`

全局单例：`settings = Settings()`

### backend/core/logger.py

结构化日志系统。

- `setup_logger(name: str) -> logging.Logger` — 创建并返回带格式化的 Logger 实例，避免重复添加 handler
- `log_agent_execution(agent_name: str) -> Callable` — **装饰器工厂**。包裹 Agent 函数，自动记录开始、完成、耗时、异常。日志标签为 `agent.{agent_name}`

日志格式：`时间 | 级别 | 模块 | 消息`

### backend/core/database.py

SQLite 持久化存储模块。自动在启动时初始化 `analyses` 表。

- `init_db()` — 创建数据库表（17 个字段含索引），应用启动时自动调用
- `save_analysis(session_id, report, jd_text, resume_snapshot)` — 保存一次完整分析。将 JSON 字段序列化存储
- `list_analyses(limit=20) -> list[dict]` — 列出历史记录（id、姓名、职位、分数、时间），按时间倒序
- `get_analysis(analysis_id) -> dict | None` — 获取单次分析完整结果，反序列化所有 JSON 字段
- `delete_analysis(analysis_id) -> bool` — 删除一次分析，返回是否成功

---

## 三、backend/schemas/ — Pydantic 数据模型

### backend/schemas/resume.py

简历结构化数据模型。

**`class ContactInfo`**：`name`, `email`, `phone`, `location`, `linkedin`, `github`（全部可选）

**`class Experience`**：`title`（职位）, `company`（公司）, `start_date`, `end_date`, `highlights: list[str]`（关键成就）

**`class Project`**：`name`, `description`（中文描述）, `technologies: list[str]`

**`class Education`**：`degree`, `institution`, `year`, `gpa`

**`class Resume`**：汇总模型，包含 `contact`, `summary`（中文个人简介）, `skills`, `experience`, `projects`, `education`, `certifications`, `languages`

### backend/schemas/jd.py

职位描述数据模型。

**`class JobDescription`**：

- `role_title: str` — 职位名称。默认空字符串，`None` 自动转换
- `department: Optional[str]` — 部门
- `seniority_level: str` — 级别：应届生/初级/中级/高级/资深/经理/总监
- `required_skills: list[str]` — 必备技能
- `preferred_skills: list[str]` — 加分技能
- `responsibilities: list[str]` — 职责
- `qualifications: list[str]` — 硬性要求
- `education_requirement: Optional[str]` — 学历要求
- `years_of_experience: Optional[float]` — 年限要求
- `keywords: list[str]` — ATS 关键词
- `industry: Optional[str]` — 行业
- `raw_text: Optional[str]` — 原始 JD 文本（序列化时排除）

**`_coerce_none_to_empty(v)`** — 字段校验器。`role_title` 和 `seniority_level` 传入 `None` 时自动转为 `""`，防止 Pydantic 校验崩溃。

### backend/schemas/ats.py

ATS 评分结果数据模型。

**`class MatchedSkill`**：`skill`（技能名）, `match_type`（exact / related / inferred）

**`class MissingSkill`**：`skill`, `importance`（required / preferred）

**`class SkillBreakdown`**：`technical_match`, `experience_match`, `education_match`, `keyword_match`（均 0-100）

**`class ATSScore`**：`overall_score`（0-100）, `matched_skills`, `missing_skills`, `skill_breakdown`, `reasoning`（中文评分理由，2-4 句）, `recommendations`（中文改进建议列表）

### backend/schemas/rewrite.py

简历改写结果数据模型。

**`class RewrittenBullet`**：`original`（原始文本）, `rewritten`（ATS 优化版，中文）, `added_keywords`（新增关键词）, `section`（段落类型：工作经历/技能/个人简介/项目经历）

**`class SkillGapAction`**：`missing_skill`（缺失技能名）, `suggestion`（中文补救建议）, `priority`（high / medium / low）

**`class RewrittenResume`**：`improved_bullets`, `suggested_summary`（优化后的中文个人简介）, `skill_gap_plan`, `keyword_additions`

### backend/schemas/interview.py

面试题数据模型。

**`class InterviewQuestion`**：`question`（中文问题）, `category`（behavioral / technical / situational / follow-up）, `difficulty`（easy / medium / hard）, `focus_area`（考察方向，中文）, `expected_topics`（期望回答要点，中文）

**`class InterviewQuestions`**：
- `behavioral_questions` — 行为面试题（团队协作、冲突处理、领导力）
- `technical_questions` — 技术面试题（核心技术、系统设计、最佳实践）
- `situational_questions` — 情景题
- `gap_probing_questions` — 缺口探测题（针对 ATS 分析中的技能缺口，委婉提问）
- `follow_up_strategy` — 面试官追问策略（中文）

### backend/schemas/report.py

最终聚合报告数据模型。

**`class PipelineMetadata`**：`started_at`, `completed_at`, 各 Agent 耗时（resume_parser / jd_analyzer / ats_scorer / rewrite_agent / interview_agent）

**`class FinalReport`**：
- `metadata` — 执行元数据
- `contact` — 候选人联系方式摘要
- `ats_summary` — ATS 评分摘要（总分 + 四维拆解 + 理由）
- `top_matched_skills` — 前 5 个匹配技能
- `critical_missing_skills` — 关键缺失技能（仅 required）
- `rewrite_highlights` — 改写亮点（前 3 条，含 before/after）
- `interview_preview` — 面试题预览（前 3 道技术题）
- `recommendations` — 改进建议

---

## 四、backend/tools/ — 工具函数

### backend/tools/pdf_parser.py

PDF 文本提取，使用 PyMuPDF (`fitz`) 库。

- `extract_text_from_pdf(file_path: str) -> str` — 从文件路径读取 PDF，逐页提取文本，返回合并后的纯文本
- `extract_text_from_pdf_bytes(content: bytes) -> str` — 从字节流读取 PDF（FastAPI 上传场景），其余同上

### backend/tools/jd_fetcher.py

职位描述 URL 抓取器。**按优先级依次尝试 4 种策略，任一成功即返回。**

- `fetch_jd_from_url(url: str, timeout: int = 15) -> str` — **主函数**。执行完整策略链。HTTP 错误和网络错误均返回中文提示
- `_default_headers() -> dict` — 返回模拟 Chrome 浏览器的 HTTP 请求头
- `_guess_site_name(url: str) -> str` — 从 URL 域名推断网站中文名
- `_extract_embedded_data(html: str) -> str` — 从 HTML `<script>` 标签提取 JSON-LD、SPA 状态数据（`__NEXT_DATA__`、`window.__INITIAL_STATE__` 等）
- `_flatten_jsonld(data) -> str` — 将 JSON-LD 结构展开为可读文本
- `_deep_extract_text(data, max_depth: int = 5) -> str` — 递归遍历嵌套 JSON，优先提取 description / title / skill 等关键字段
- `_clean_text(text: str) -> str` — 清洗 HTML 实体、转义字符、多余空白
- `_strip_html(html: str) -> str` — 从 HTML 源码移除标签提取纯文本
- `_fetch_with_browser(url: str, timeout: int) -> str | None` — **Playwright 无头浏览器**。启动 Chromium 渲染 JS 页面并提取可见文本。未安装则静默跳过

**抓取策略链**：内嵌 script 数据 → HTML 纯文本 → Playwright 浏览器渲染 → 报错提示手动粘贴

---

## 五、backend/agents/ — AI Agent

每个 Agent 文件均包含：Prompt 模板、JSON 修复 Prompt、JSON 提取函数、Qwen 调用函数、主 Agent 函数。

### backend/agents/resume_parser.py

**简历解析 Agent**。模型：`qwen-turbo`（重试用 `qwen-plus`）。

- `RESUME_EXTRACTION_PROMPT` — 系统提示词。要求 LLM 从简历文本提取 contact / summary / skills / experience / projects / education 等字段的 JSON。占位符 `{resume_text}`
- `FIX_JSON_PROMPT` — JSON 修复提示词。LLM 返回的 JSON 无法解析时，用此提示词让更强模型修复。占位符 `{raw_text}`
- `_extract_json_from_text(text: str) -> dict | None` — 从 LLM 返回文本中提取 JSON。依次尝试：直接解析 → 提取 markdown 代码块 → 正则匹配大括号
- `_call_qwen(prompt: str, model: str | None) -> str` — 调用 DashScope Qwen 模型。设置 API key，发送消息，检查状态码，返回响应文本
- `parse_resume(resume_text: str, max_retries: int = 2) -> Resume` — **主函数**。截断超长文本到 12000 字，调用 Qwen 提取，解析 JSON，失败则用 `qwen-plus` 重试最多 2 次，返回 `Resume` 对象
- `parse_resume_from_pdf(pdf_path: str) -> Resume` — 便捷函数。先调 `extract_text_from_pdf` 再调 `parse_resume`

### backend/agents/jd_analyzer.py

**JD 分析 Agent**。模型：`qwen-turbo`（重试用 `qwen-plus`）。

- `JD_EXTRACTION_PROMPT` — 提示词模板。提取职位名称 / 级别 / 必备技能 / 加分技能 / 职责 / 要求 / 关键词。强调 role_title 和 seniority_level 不能为 null。占位符 `{jd_text}`
- `FIX_JSON_PROMPT` — JSON 修复提示词。占位符 `{raw_text}`
- `analyze_jd(jd_text: str, max_retries: int = 2) -> JobDescription` — **主函数**。分析 JD 文本并返回结构化 `JobDescription`
- `analyze_jd_from_url(url: str) -> JobDescription` — 便捷函数。先调 `fetch_jd_from_url` 再调 `analyze_jd`

### backend/agents/ats_scorer.py

**ATS 评分 Agent**。模型：`qwen-plus`（重试用 `qwen-plus`）。

- `ATS_SCORING_PROMPT` — 提示词模板。对比简历 JSON 和 JD JSON，输出评分 / 匹配技能 / 缺失技能 / 四维拆解 / 理由 / 建议。占位符 `{resume_json}` 和 `{jd_json}`
- `FIX_JSON_PROMPT` — JSON 修复提示词。占位符 `{raw_text}`
- `score_ats(resume: Resume, jd: JobDescription, max_retries: int = 2) -> ATSScore` — **主函数**。将 Resume 和 JobDescription 序列化为 JSON，调用 Qwen 评分。包含嵌套对象（MatchedSkill、MissingSkill、SkillBreakdown）的规范化处理

### backend/agents/rewrite_agent.py

**简历改写 Agent**。模型：`qwen-plus`（重试用 `qwen-plus`）。

- `REWRITE_PROMPT` — 提示词模板。基于简历 + JD + ATS 分析，输出改写后的 bullet（含 before/after）、优化后个人简介、技能缺口补救计划。占位符 `{resume_json}` `{jd_json}` `{ats_json}`
- `FIX_JSON_PROMPT` — JSON 修复提示词。占位符 `{raw_text}`
- `rewrite_resume(resume: Resume, jd: JobDescription, ats: ATSScore, max_retries: int = 2) -> RewrittenResume` — **主函数**。生成 ATS 优化建议。规则：不编造经历、自然融入关键词、量化成果、用有力动词

### backend/agents/interview_agent.py

**面试题生成 Agent**。模型：`qwen-plus`（重试用 `qwen-plus`）。

- `INTERVIEW_PROMPT` — 提示词模板。生成 4 类面试题（行为 / 技术 / 情景 / 缺口探测）+ 追问策略。全部中文输出。占位符 `{resume_json}` `{jd_json}` `{ats_json}`
- `FIX_JSON_PROMPT` — JSON 修复提示词。占位符 `{raw_text}`
- `_normalize_questions(data: dict, key: str) -> list[InterviewQuestion]` — 将 JSON 字典列表转换为 `InterviewQuestion` 对象列表
- `generate_interview_questions(resume: Resume, jd: JobDescription, ats: ATSScore, max_retries: int = 2) -> InterviewQuestions` — **主函数**。生成全套面试题

---

## 六、backend/workflows/ — LangGraph 编排

### backend/workflows/state.py

管道状态定义。

- `_reduce_error(current: str, update: str) -> str` — **并行合并函数**。多个节点同时写入 `error` 时，保留第一个错误（不覆盖）
- `_reduce_stage(current: str, update: str) -> str` — **并行合并函数**。多个节点同时写入 `current_stage` 时，取最新值
- `class PipelineState(TypedDict)` — LangGraph 状态字典。包含：

输入字段：`pdf_path`, `jd_text`, `jd_url`

中间结果：`resume`, `jd`, `ats`, `rewritten_resume`, `interview_questions`, `final_report`

计时：`resume_parser_duration_s`, `jd_analyzer_duration_s`, `ats_scorer_duration_s`, `rewrite_agent_duration_s`, `interview_agent_duration_s`

控制：`error`（Annotated + _reduce_error）, `current_stage`（Annotated + _reduce_stage）, `session_id`

### backend/workflows/progress.py

进度追踪模块，线程安全。后台管道节点通过 `session_id` 写入当前阶段，前端轮询读取。

- `STEPS` / `STEP_LABELS` — 5 个步骤的 key 与中文名映射
- `create_session() -> str` — 创建新会话，返回 12 位 session_id
- `update_progress(session_id, stage)` — 记录节点完成状态。管道每节点完成后调用
- `get_progress(session_id) -> dict | None` — 获取会话进度（completed 列表 + current 阶段）
- `set_result(session_id, result)` — 存储管道最终结果
- `get_result(session_id) -> dict | None` — 获取管道最终结果
- `cleanup_session(session_id)` — 清理已完成会话

### backend/workflows/graph.py

LangGraph 工作流图定义。**两层并行执行。**

图拓扑：

```
              START
              ┌───┴───┐
              ↓       ↓
        parse_resume  analyze_jd     ← L1 并行
              └───┬───┘
                  ↓
              score_ats
              ┌───┴───┐
              ↓       ↓
           rewrite  interview        ← L2 并行
              └───┬───┘
                  ↓
          aggregate_report
                  ↓
                 END
```

**节点函数**：

- `_parse_resume_node(state) -> dict` — **节点 1a**。PDF 提取 + 简历解析，更新 `resume` / `resume_raw_text` / `resume_parser_duration_s`
- `_analyze_jd_node(state) -> dict` — **节点 1b**。JD 分析，更新 `jd` / `jd_analyzer_duration_s`
- `_score_ats_node(state) -> dict` — **节点 2**。等待 L1 两个节点都完成后执行。重建 Resume 和 JobDescription，评分，更新 `ats` / `ats_scorer_duration_s`
- `_rewrite_node(state) -> dict` — **节点 3a**。简历改写，更新 `rewritten_resume` / `rewrite_agent_duration_s`
- `_interview_node(state) -> dict` — **节点 3b**。面试题生成，更新 `interview_questions` / `interview_agent_duration_s`
- `_aggregate_report_node(state) -> dict` — **节点 4**。等待 L2 两个节点都完成后执行。汇总所有结果生成 `FinalReport`

**路由和构建**：

- `_route_on_error(state) -> str` — 条件路由。检查 error，有则跳过后续去 aggregate_report
- `build_pipeline_graph() -> StateGraph` — 创建 StateGraph，添加 6 个节点，配置边，编译并返回
- `get_pipeline() -> StateGraph` — 全局单例，缓存编译后的图
- `run_pipeline(pdf_path, jd_text, jd_url) -> PipelineState` — **对外入口**。构建初始状态，调用 `pipeline.invoke()`。最外层 try/except 捕获 LangGraph 异常

**边配置**：

- `START → parse_resume`，`START → analyze_jd`（L1 并行）
- `parse_resume → score_ats`（条件：有 error 则 → aggregate_report）
- `analyze_jd → score_ats`（条件：同上）
- `score_ats → rewrite`，`score_ats → interview`（L2 并行）
- `rewrite → aggregate_report`，`interview → aggregate_report`（汇聚）
- `aggregate_report → END`

---

## 七、backend/api/ — FastAPI 接口

### backend/api/main.py

FastAPI 应用主文件。配置 CORS 中间件（允许 localhost:3000 / 3001），注册调试路由。

- `startup()` — 启动事件。校验配置，打印日志
- `root()` — `GET /` — 返回服务信息
- `health()` — `GET /health` — 健康检查
- `analyze(resume_pdf, jd_text, jd_url)` — **`POST /analyze`** — 核心端点。后台线程执行管道，立即返回 `{session_id}`，前端通过 `/progress/{id}` 轮询进度，完成后通过 `/result/{id}` 获取报告
- `progress(session_id)` — `GET /progress/{session_id}` — 查询管道进度（completed 列表 + 总步数）
- `get_analysis_result(session_id)` — `GET /result/{session_id}` — 获取后台分析结果，完成后自动清理会话
- `list_history(limit)` — `GET /history` — 列出历史分析记录
- `get_history(analysis_id)` — `GET /history/{id}` — 获取一次历史分析的完整结果
- `delete_history(analysis_id)` — `DELETE /history/{id}` — 删除一条历史记录

### backend/api/debug_routes.py

**5 个调试端点**（前缀 `/debug`），每个可独立测试一个阶段。

- `debug_parse_resume(resume_pdf)` — `POST /debug/parse-resume` — 仅 PDF 提取 + 简历解析
- `debug_analyze_jd(jd_text, jd_url)` — `POST /debug/analyze-jd` — 仅 JD 分析
- `debug_score_ats(resume_pdf, jd_text, jd_url)` — `POST /debug/score-ats` — 跑完前三步到 ATS 评分
- `debug_rewrite(resume_pdf, jd_text, jd_url)` — `POST /debug/rewrite` — 跑完前四步到简历改写
- `debug_interview(resume_pdf, jd_text, jd_url)` — `POST /debug/interview` — 跑完前五步到面试题
- `_save_upload(file: UploadFile) -> Path` — 内部工具。保存上传 PDF 到临时目录

---

## 八、frontend/ — Next.js 前端

### 配置文件

**`next.config.ts`** — `rewrites` 规则将 `/api/*` 转发到 `http://localhost:8000/*`（备用代理，前

端已改为直连）

**`tailwind.config.ts`** — TailwindCSS 配置。扩展 `primary` 色板（蓝色系）、`fade-in` 和 `slide-up` 动画

**`tsconfig.json`** — TypeScript 配置。路径别名 `@/*` → `./src/*`

**`postcss.config.mjs`** — PostCSS 配置。加载 tailwindcss 和 autoprefixer 插件

### frontend/src/app/layout.tsx

根布局。设置 HTML `lang="en"`，引入 Inter 字体，导入全局 CSS。metadata 标题为"AI 求职助手 — 智能简历分析"。

### frontend/src/app/globals.css

全局样式。Tailwind 指令 + CSS 变量（背景色、前景色、边框色）+ `.score-ring` 圆环评分样式。

### frontend/src/app/page.tsx

**主页面**（唯一页面）。单页应用，三个状态切换：

- `"form"` — 上传表单 + 底部"历史记录"按钮 → 右侧滑出历史抽屉
- `"loading"` — 5 步进度条，每步完成亮绿色对勾，当前步显示旋转动画。每 1.5s 轮询后端进度
- `"results"` — 评分仪表盘 + 四维评分卡 + 简历优化建议（全部展示，默认折叠，可展开）+ 面试题四分类 Tab（技术/行为/情景/缺口）+ 改进建议 + 分享链接按钮 + 重新分析

核心函数：

- `handleSubmit()` — 提交 → 得 session_id → 轮询进度 → 全部完成取结果
- `reset()` — 返回表单，清空状态
- `loadHistory()` — 加载历史记录列表
- 分享链接加载 — 页面 URL 带 `?share=xxx` 时自动加载对应分析结果

本地映射常量：

- `DIFFICULTY_MAP` — hard → "困难", medium → "中等", easy → "简单"
- `BREAKDOWN_LABELS` — Technical → "技术匹配", Experience → "经验匹配", Education → "学历匹配", Keywords → "关键词"

### frontend/src/components/score-gauge.tsx

SVG 圆环评分仪表盘。

**Props**：`score: number`（0-100）, `size: "sm" | "lg"`（默认 160px）

- `getScoreColor(score: number) -> string` — 80+ 绿色，60+ 黄色，<60 红色

### frontend/src/components/skill-badge.tsx

技能标签。

**Props**：`skill: string`, `variant: "matched" | "missing"`

匹配显示绿色 `+`，缺失显示红色 `-`。

### frontend/src/components/rewrite-card.tsx

简历改写对比卡片。

**Props**：`section: string`, `original: string`, `rewritten: string`

内置 `SECTION_LABELS` 映射表（experience → 工作经历，projects → 项目经历 等），支持中英文自动转换。

### frontend/src/lib/types.ts

TypeScript 类型定义。与后端 Pydantic 模型一一对应：

`Contact`, `ATSSummary`, `RewriteHighlight`, `InterviewPreview`, `Metadata`, `Report`, `AnalyzeResponse`

### frontend/src/lib/api.ts

API 客户端。

- `submitAnalysis(file, jdText, jdUrl) -> string` — POST `/analyze`，返回 session_id
- `getProgress(sessionId) -> ProgressResponse` — GET `/progress/{id}`，返回已完成步骤列表
- `getResult(sessionId) -> AnalyzeResponse` — GET `/result/{id}`，获取最终报告
- `getHistory() -> HistoryItem[]` — GET `/history`，列出历史记录
- `getHistoryDetail(id) -> AnalyzeResponse` — GET `/history/{id}`，获取历史详情
- `deleteHistoryItem(id) -> void` — DELETE `/history/{id}`
- `checkHealth() -> boolean` — GET `/health`

API 地址：`process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`

### frontend/src/lib/utils.ts

- `cn(...inputs) -> string` — TailwindCSS 类名合并
- `formatDuration(seconds) -> string` — 秒数格式化

---

## 九、tests/ — 测试脚本

每个阶段一个测试脚本，可独立运行。

### tests/test_phase1.py

**阶段一测试**：配置加载 + DashScope 连通性 + PDF 提取 + 简历解析。

用法：`python tests/test_phase1.py --pdf resume.pdf`

### tests/test_phase2.py

**阶段二测试**：JD 分析 + ATS 评分。内置示例简历和 JD 数据，无需外部文件。

用法：`python tests/test_phase2.py` 或 `python tests/test_phase2.py --url "..."`

### tests/test_phase3.py

**阶段三测试**：简历改写 + 面试题生成。

用法：`python tests/test_phase3.py`

### tests/test_phase4.py

**阶段四测试**：完整 LangGraph 管道。自动生成测试 PDF。

用法：`python tests/test_phase4.py` 或 `python tests/test_phase4.py --pdf resume.pdf`

### tests/test_phase5.py

**阶段五测试**：FastAPI 端点。需先启动后端 `python run.py --port 8000`。

用法：`python tests/test_phase5.py`

---

## 十、数据流完整路径

```
用户操作（前端 http://localhost:3001）
  │
  ├─ 拖拽/选择 PDF 文件
  ├─ 粘贴 JD 文本（或输入 URL）
  └─ 点击"开始分析"
          │
          ▼
  POST /analyze → 返回 {session_id}（后台线程启动管道）
          │
          ▼
  GET /progress/{id} ← 每 1.5s 轮询，5 步逐一打勾
          │
  ┌───────┴────────┐              ← L1 并行（qwen-turbo）
  ▼                ▼
parse_resume    analyze_jd
  │                │
  └──────┬─────────┘
         ▼
     score_ats                     ← qwen-plus
         │
  ┌──────┴──────┐                  ← L2 并行（qwen-plus）
  ▼             ▼
rewrite      interview
  │             │
  └──────┬──────┘
         ▼
  aggregate_report → save_analysis() → SQLite
         │
         ▼
  GET /result/{id} → FinalReport JSON
         │
         ▼
  前端结果展示
  ├── 评分仪表盘（0-100 环形图）
  ├── 四维评分卡（技术/经验/学历/关键词）
  ├── 简历优化建议（全部展示，默认折叠可展开）
  ├── 面试题四分类 Tab（技术/行为/情景/缺口）
  ├── 改进建议列表
  ├── [分享链接] 按钮
  └── [重新分析] 按钮
```
