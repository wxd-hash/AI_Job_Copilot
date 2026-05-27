import json
import re
from typing import Optional

import dashscope
from dashscope import Generation

from backend.core.config import settings
from backend.core.logger import setup_logger, log_agent_execution
from backend.schemas.jd import JobDescription

logger = setup_logger("agent.jd_analyzer")

JD_EXTRACTION_PROMPT = """你是一位职位描述分析专家。请根据招聘信息文本，提取结构化数据，输出为合法 JSON。

JSON 字段说明（全部必填，字符串/数组字段永远不要返回 null）：
- role_title: string（职位名称——必须推断，不能为 null）
- department: string 或 null（部门/团队）
- seniority_level: string（必须——从以下选择：应届生、初级、中级、高级、资深、经理、总监）
- required_skills: string[]（必备的技术和软技能——没有则为 []）
- preferred_skills: string[]（加分技能——"优先""加分""nice to have"等描述——没有则为 []）
- responsibilities: string[]（主要职责——没有则为 []）
- qualifications: string[]（学历/证书等硬性要求——没有则为 []）
- education_requirement: string 或 null（最低学历要求）
- years_of_experience: number 或 null（要求的工作年限，数字）
- keywords: string[]（重要 ATS 关键词——工具、框架、证书、方法论——没有则为 []）
- industry: string 或 null（所属行业）

关键规则：
1. role_title 和 seniority_level 必须是真实字符串，永远不能为 null。如果文本不完整，请根据可用线索（URL、标题片段、技能模式）做最佳推断。
2. 区分 required_skills 和 preferred_skills（"必须""必备"→ required，"优先""加分"→ preferred）。
3. 所有文字内容用中文输出，技能名等专有名词保留原文。
4. 仅返回合法 JSON，不要 markdown 标记，不要其他解释。

招聘信息文本：
{jd_text}"""

FIX_JSON_PROMPT = """以下文本应为合法 JSON 但无法解析，请修复并仅返回合法 JSON，不要 markdown，不要解释。

待修复文本：
{raw_text}

期望的 JSON 结构：
- role_title: string
- department: string 或 null
- seniority_level: string（应届生、初级、中级、高级、资深、经理、总监）
- required_skills: string[]
- preferred_skills: string[]
- responsibilities: string[]
- qualifications: string[]
- education_requirement: string 或 null
- years_of_experience: number 或 null
- keywords: string[]
- industry: string 或 null

仅返回修复后的 JSON："""


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


def _call_qwen(prompt: str, model: str | None = None) -> str:
    dashscope.api_key = settings.DASHSCOPE_API_KEY
    model = model or settings.MODEL_NAME

    response = Generation.call(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"DashScope API error: code={response.code}, message={response.message}"
        )

    return response.output.choices[0].message.content


@log_agent_execution("jd_analyzer")
def analyze_jd(jd_text: str, max_retries: int = 2) -> JobDescription:
    """
    Analyze a job description and extract structured data using Qwen.

    Args:
        jd_text: Raw text of the job description.
        max_retries: Maximum retries for JSON parsing failures.

    Returns:
        Validated JobDescription Pydantic object.
    """
    text = jd_text[:12000]

    prompt = JD_EXTRACTION_PROMPT.format(jd_text=text)
    raw_output = _call_qwen(prompt, model=settings.MODEL_NAME_SIMPLE)
    logger.info("Qwen response received, length=%d", len(raw_output))

    data = _extract_json_from_text(raw_output)

    for attempt in range(max_retries):
        if data is not None:
            break
        logger.warning("JSON parse failed, retry %d/%d", attempt + 1, max_retries)
        fix_prompt = FIX_JSON_PROMPT.format(raw_text=raw_output)
        raw_output = _call_qwen(fix_prompt, model=settings.MODEL_NAME)
        data = _extract_json_from_text(raw_output)

    if data is None:
        raise ValueError(
            f"Failed to parse JSON from Qwen output after {max_retries} retries"
        )

    jd = JobDescription(**data)
    jd.raw_text = jd_text
    return jd


@log_agent_execution("jd_analyzer_from_url")
def analyze_jd_from_url(url: str) -> JobDescription:
    """Fetch a JD from a URL and analyze it."""
    from backend.tools.jd_fetcher import fetch_jd_from_url

    text = fetch_jd_from_url(url)
    return analyze_jd(text)
