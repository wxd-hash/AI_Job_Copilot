import json
import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.core.config import settings
from backend.core.logger import setup_logger, log_agent_execution
from backend.agents.llm import DashScopeChatModel
from backend.schemas.resume import Resume

logger = setup_logger("agent.resume_parser")

RESUME_EXTRACTION_PROMPT = """你是一位简历解析专家。请根据从 PDF 中提取的原始文本，提取以下结构化信息，输出为合法 JSON。

JSON 字段说明（仅返回 JSON，不要任何其他内容）：
- contact: {{name, email, phone, location, linkedin, github}}（没有的字段省略）
- summary: string（个人简介，中文描述，如无则为 null）
- skills: string[]（技术技能和软技能，保留原始英文技能名）
- experience: [{{title, company, start_date, end_date, highlights: string[]}}]（工作经历，highlights 用中文描述）
- projects: [{{name, description, technologies: string[]}}]（项目经历，description 用中文描述）
- education: [{{degree, institution, year, gpa}}]（学历信息）
- certifications: string[]（证书列表）
- languages: string[]（语言能力）

规则：
1. 从上下文推断技能——包括明显列出的和从项目/经历中能看出的。
2. 日期格式尽量用 "YYYY-MM"，或 "YYYY"，不确定则为 null。
3. 简历中没有的部分返回空数组或 null。
4. 所有文字内容用中文输出，技能名等专有名词保留原文。
5. 仅返回合法 JSON，不要 markdown 标记，不要其他解释。

简历文本：
{resume_text}"""

FIX_JSON_PROMPT = """以下文本应为合法 JSON 但无法解析，请修复并仅返回合法 JSON，不要 markdown，不要解释。

待修复文本：
{raw_text}

期望的 JSON 结构：
- contact: {{name, email, phone, location, linkedin, github}}
- summary: string 或 null
- skills: string[]
- experience: [{{title, company, start_date, end_date, highlights: string[]}}]
- projects: [{{name, description, technologies: string[]}}]
- education: [{{degree, institution, year, gpa}}]
- certifications: string[]
- languages: string[]

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


@log_agent_execution("resume_parser")
def parse_resume(resume_text: str, max_retries: int = 2) -> Resume:
    text = resume_text[:12000]

    model = DashScopeChatModel(model=settings.MODEL_NAME_SIMPLE, temperature=0.1)
    chain = ChatPromptTemplate.from_template(RESUME_EXTRACTION_PROMPT) | model | StrOutputParser()

    raw_output = chain.invoke({"resume_text": text})
    logger.info("Qwen response received, length=%d", len(raw_output))

    data = _extract_json_from_text(raw_output)

    for attempt in range(max_retries):
        if data is not None:
            break
        logger.warning("JSON parse failed, retry attempt %d/%d", attempt + 1, max_retries)
        fix_model = DashScopeChatModel(model=settings.MODEL_NAME, temperature=0.1)
        fix_chain = ChatPromptTemplate.from_template(FIX_JSON_PROMPT) | fix_model | StrOutputParser()
        raw_output = fix_chain.invoke({"raw_text": raw_output})
        data = _extract_json_from_text(raw_output)

    if data is None:
        raise ValueError(f"Failed to parse JSON from Qwen output after {max_retries} retries")

    return Resume(**data)


def parse_resume_from_pdf(pdf_path: str) -> Resume:
    from backend.tools.pdf_parser import extract_text_from_pdf
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        raise ValueError(f"No text extracted from PDF: {pdf_path}")
    logger.info("Extracted %d chars from PDF", len(text))
    return parse_resume(text)
