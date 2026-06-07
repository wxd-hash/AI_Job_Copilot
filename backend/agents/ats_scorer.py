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
from backend.schemas.ats import ATSScore, MatchedSkill, MissingSkill, SkillBreakdown

logger = setup_logger("agent.ats_scorer")

ATS_SCORING_PROMPT = """你是一位资深 ATS（简历筛选系统）评估专家。请根据候选人的简历和职位描述，生成详细的匹配度分析报告。

仅返回 JSON 对象，字段如下：
- overall_score: integer 0-100（综合匹配度百分比）
- matched_skills: array of {{"skill": string, "match_type": "exact"|"related"|"inferred"}}（匹配的技能，exact=精确匹配, related=相关技能, inferred=推断匹配）
- missing_skills: array of {{"skill": string, "importance": "required"|"preferred"}}（缺失的技能，required=必备, preferred=加分）
- skill_breakdown: {{
    "technical_match": number 0-100（技术匹配度）,
    "experience_match": number 0-100（经验匹配度）,
    "education_match": number 0-100（学历匹配度）,
    "keyword_match": number 0-100（关键词匹配度）
  }}
- reasoning: string（用 2-4 句中文详细解释综合评分的依据）
- recommendations: string[]（3-5 条中文 actionable 建议，用于提高匹配度）

评分准则：
- technical_match：简历技能 vs JD 必备+加分技能的重合度
- experience_match：工作经验的关联度、年限、职位级别、行业领域
- education_match：学历水平与专业相关度
- keyword_match：JD 关键词在简历中的出现密度
- overall_score：加权平均——技术 40%、经验 30%、学历 15%、关键词 15%
- 实事求是——不要虚高打分

仅返回合法 JSON，不要 markdown 标记，不要其他解释。

---
简历：
{resume_json}

---
职位描述：
{jd_json}"""

FIX_JSON_PROMPT = """Fix the following text to be valid JSON matching this schema:
{{
  "overall_score": integer 0-100,
  "matched_skills": [{{"skill": string, "match_type": "exact"|"related"|"inferred"}}],
  "missing_skills": [{{"skill": string, "importance": "required"|"preferred"}}],
  "skill_breakdown": {{
    "technical_match": number 0-100,
    "experience_match": number 0-100,
    "education_match": number 0-100,
    "keyword_match": number 0-100
  }},
  "reasoning": string,
  "recommendations": string[]
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


@log_agent_execution("ats_scorer")
def score_ats(resume: Resume, jd: JobDescription, max_retries: int = 2) -> ATSScore:
    resume_json = resume.model_dump_json(exclude_none=True, indent=2)
    jd_json = jd.model_dump_json(exclude={"raw_text"}, exclude_none=True, indent=2)

    model = DashScopeChatModel(model=settings.MODEL_NAME_COMPLEX, temperature=0.1)
    chain = ChatPromptTemplate.from_template(ATS_SCORING_PROMPT) | model | StrOutputParser()

    raw_output = chain.invoke({"resume_json": resume_json, "jd_json": jd_json})
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
        raise ValueError(f"Failed to parse ATS score JSON after {max_retries} retries")

    if "matched_skills" in data:
        data["matched_skills"] = [
            MatchedSkill(**m) if isinstance(m, dict) else m for m in data["matched_skills"]
        ]
    if "missing_skills" in data:
        data["missing_skills"] = [
            MissingSkill(**m) if isinstance(m, dict) else m for m in data["missing_skills"]
        ]
    if "skill_breakdown" in data and isinstance(data["skill_breakdown"], dict):
        data["skill_breakdown"] = SkillBreakdown(**data["skill_breakdown"])

    return ATSScore(**data)
