import json
import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.core.config import settings
from backend.core.logger import setup_logger, log_agent_execution
from backend.agents.llm import DashScopeChatModel
from backend.schemas.resume import Resume
from backend.schemas.jd import JobDescription
from backend.schemas.ats import ATSScore
from backend.schemas.rewrite import RewrittenResume, RewrittenBullet, SkillGapAction

logger = setup_logger("agent.rewrite")

REWRITE_PROMPT = """你是一位资深简历优化专家，专精于 ATS（简历筛选系统）优化。请根据候选人的简历、职位描述和 ATS 匹配分析，优化简历内容以最大化 ATS 兼容性。

仅返回 JSON 对象，字段如下：
- improved_bullets: array of {{
    "original": string（原始描述）,
    "rewritten": string（ATS 优化版本，自然地融入 JD 关键词，中文表达）,
    "added_keywords": string[]（本条新增的关键词）,
    "section": string（段落类型："工作经历"/"技能"/"个人简介"/"项目经历"）
  }}
  （选择 5-8 条最有优化空间的来改写。绝不编造经历——仅优化措辞，突出相关现有技能。）
- suggested_summary: string（2-3 句中文个人简介，自然地融入 JD 核心关键词）
- skill_gap_plan: array of {{
    "missing_skill": string（缺失技能名）,
    "suggestion": string（中文建议——如何弥补：学习方法、关联经验、或表达学习意愿）,
    "priority": string（优先级：high/medium/low）
  }}
  （ATS 分析中每个缺失技能对应一条。）
- keyword_additions: string[]（简历中新增的全部 JD 关键词）

规则：
1. 绝不编造候选人不具备的经历。
2. 自然地使用 JD 关键词——不要堆砌。
3. 尽可能量化成果（从上下文提取数字）。
4. 使用有力的动词（主导、设计、架构、优化等）。
5. 保留相同的实际内容——仅改善表达和关键词匹配。
6. 优化后的内容用中文表达，技能名称保留原文。
7. 仅返回合法 JSON，不要 markdown 标记，不要其他解释。

---
简历：
{resume_json}

---
职位描述：
{jd_json}

---
ATS 分析：
{ats_json}"""

FIX_JSON_PROMPT = """Fix the following text to be valid JSON matching this schema:
{{
  "improved_bullets": [{{"original": string, "rewritten": string, "added_keywords": string[], "section": string}}],
  "suggested_summary": string,
  "skill_gap_plan": [{{"missing_skill": string, "suggestion": string, "priority": "high"|"medium"|"low"}}],
  "keyword_additions": string[]
}}

Return ONLY the fixed JSON, no markdown, no commentary.

Text to fix:
{raw_text}"""


def _extract_json_from_text(text: str) -> Optional[dict]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


@log_agent_execution("rewrite_agent")
def rewrite_resume(
    resume: Resume, jd: JobDescription, ats: ATSScore, max_retries: int = 2
) -> RewrittenResume:
    resume_json = resume.model_dump_json(exclude_none=True, indent=2)
    jd_json = jd.model_dump_json(exclude={"raw_text"}, exclude_none=True, indent=2)
    ats_json = ats.model_dump_json(exclude_none=True, indent=2)

    model = DashScopeChatModel(model=settings.MODEL_NAME_COMPLEX, temperature=0.1)
    chain = ChatPromptTemplate.from_template(REWRITE_PROMPT) | model | StrOutputParser()

    raw_output = chain.invoke({"resume_json": resume_json, "jd_json": jd_json, "ats_json": ats_json})
    logger.info("Qwen response received, length=%d", len(raw_output))

    data = _extract_json_from_text(raw_output)

    for attempt in range(max_retries):
        if data is not None:
            break
        logger.warning("JSON parse failed, retry %d/%d", attempt + 1, max_retries)
        fix_model = DashScopeChatModel(model=settings.MODEL_NAME_COMPLEX, temperature=0.1)
        fix_chain = ChatPromptTemplate.from_template(FIX_JSON_PROMPT) | fix_model | StrOutputParser()
        raw_output = fix_chain.invoke({"raw_text": raw_output})
        data = _extract_json_from_text(raw_output)

    if data is None:
        raise ValueError(f"Failed to parse rewrite JSON after {max_retries} retries")

    if "improved_bullets" in data:
        data["improved_bullets"] = [
            RewrittenBullet(**b) if isinstance(b, dict) else b for b in data["improved_bullets"]
        ]
    if "skill_gap_plan" in data:
        data["skill_gap_plan"] = [
            SkillGapAction(**s) if isinstance(s, dict) else s for s in data["skill_gap_plan"]
        ]

    return RewrittenResume(**data)
