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
from backend.schemas.interview import InterviewQuestions, InterviewQuestion

logger = setup_logger("agent.interview")

INTERVIEW_PROMPT = """你是一家顶尖科技公司的资深技术面试官。请根据候选人简历、职位描述和 ATS 匹配分析，生成一套全面的中文面试题。

仅返回 JSON 对象，字段如下：
- behavioral_questions: array of {{
    "question": string（面试问题，中文）,
    "category": "behavioral",
    "difficulty": "easy"|"medium"|"hard"（简单/中等/困难）,
    "focus_area": string（考察方向，中文）,
    "expected_topics": string[]（期望回答涵盖的要点，中文）
  }}
  （3-4 题，覆盖团队协作、冲突处理、领导力、项目主导能力。务必结合候选人的实际经历提问。）
- technical_questions: array of {{
    "question": string（技术问题，中文）,
    "category": "technical",
    "difficulty": "easy"|"medium"|"hard",
    "focus_area": string,
    "expected_topics": string[]
  }}
  （4-5 题，覆盖核心技术、系统设计、最佳实践、调试能力。深入候选人的已有技能，同时探测 JD 要求但简历中缺失的技能。）
- situational_questions: array of {{
    "question": string（情景题，中文）,
    "category": "situational",
    "difficulty": "easy"|"medium"|"hard",
    "focus_area": string,
    "expected_topics": string[]
  }}
  （2-3 题，与职位和候选人背景相关的情景题。）
- gap_probing_questions: array of {{
    "question": string（缺口探测题，中文）,
    "category": "follow-up",
    "difficulty": "easy"|"medium"|"hard",
    "focus_area": string,
    "expected_topics": string[]
  }}
  （2-3 题，针对 ATS 分析中的技能缺口。以委婉方式提问——评估候选人的学习能力和关联经验，而非质问其缺失。）
- follow_up_strategy: string（2-3 句中文，面试官使用追问策略的总体指导）

规则：
1. 问题必须针对候选人的具体简历——引用他们的实际经历、项目和技术栈。
2. 难度与 JD 中的级别匹配。
3. 缺口探测题要委婉得体——评估而非审问。
4. 每题注明 expected_topics，让面试官知道优质回答应包含哪些要点。
5. 所有问题用中文输出，技术术语保留原文。
6. 仅返回合法 JSON，不要 markdown 标记，不要其他解释。

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
  "behavioral_questions": [{{"question": string, "category": "behavioral", "difficulty": "easy"|"medium"|"hard", "focus_area": string, "expected_topics": string[]}}],
  "technical_questions": [{{"question": string, "category": "technical", "difficulty": "easy"|"medium"|"hard", "focus_area": string, "expected_topics": string[]}}],
  "situational_questions": [{{"question": string, "category": "situational", "difficulty": "easy"|"medium"|"hard", "focus_area": string, "expected_topics": string[]}}],
  "gap_probing_questions": [{{"question": string, "category": "follow-up", "difficulty": "easy"|"medium"|"hard", "focus_area": string, "expected_topics": string[]}}],
  "follow_up_strategy": string
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


def _normalize_questions(data: dict, key: str) -> list[InterviewQuestion]:
    items = data.get(key, [])
    return [InterviewQuestion(**q) if isinstance(q, dict) else q for q in items]


@log_agent_execution("interview_agent")
def generate_interview_questions(
    resume: Resume, jd: JobDescription, ats: ATSScore, max_retries: int = 2
) -> InterviewQuestions:
    resume_json = resume.model_dump_json(exclude_none=True, indent=2)
    jd_json = jd.model_dump_json(exclude={"raw_text"}, exclude_none=True, indent=2)
    ats_json = ats.model_dump_json(exclude_none=True, indent=2)

    model = DashScopeChatModel(model=settings.MODEL_NAME_COMPLEX, temperature=0.1)
    chain = ChatPromptTemplate.from_template(INTERVIEW_PROMPT) | model | StrOutputParser()

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
        raise ValueError(f"Failed to parse interview JSON after {max_retries} retries")

    for key in ["behavioral_questions", "technical_questions", "situational_questions", "gap_probing_questions"]:
        data[key] = _normalize_questions(data, key)

    return InterviewQuestions(**data)
