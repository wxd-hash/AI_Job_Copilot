"""Debug endpoints — 每个 Agent 独立调用，方便定位问题。"""

import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from backend.core.logger import setup_logger

logger = setup_logger("api.debug")
router = APIRouter(prefix="/debug", tags=["debug"])


def _save_upload(file: UploadFile) -> Path:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "必须上传 .pdf 文件")
    content = file.file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "PDF 超过 10MB")
    tmp_dir = Path(tempfile.gettempdir()) / "ai_job_copilot_debug"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4().hex}_{file.filename}"
    tmp_path.write_bytes(content)
    return tmp_path


# ═══════════════════════════════════════════════════════════════════════
# Step 1: 简历解析
# ═══════════════════════════════════════════════════════════════════════

@router.post("/parse-resume")
async def debug_parse_resume(
    resume_pdf: UploadFile = File(..., description="简历 PDF"),
):
    """上传简历 PDF，仅测试 PDF 提取 + 简历解析，返回结构化 Resume JSON。"""
    tmp_path = _save_upload(resume_pdf)
    try:
        from backend.tools.pdf_parser import extract_text_from_pdf
        from backend.agents.resume_parser import parse_resume

        raw = extract_text_from_pdf(str(tmp_path))
        resume = parse_resume(raw)
        return JSONResponse({
            "step": "parse_resume",
            "status": "ok",
            "raw_chars": len(raw),
            "resume": resume.model_dump(exclude_none=True),
        })
    except Exception as e:
        return JSONResponse({"step": "parse_resume", "status": "error", "error": str(e)})
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ═══════════════════════════════════════════════════════════════════════
# Step 2: JD 分析
# ═══════════════════════════════════════════════════════════════════════

@router.post("/analyze-jd")
async def debug_analyze_jd(
    jd_text: str = Form(default="", description="JD 文本"),
    jd_url: str = Form(default="", description="或 JD URL"),
):
    """仅测试 JD 分析，返回结构化 JobDescription JSON。"""
    if not jd_text.strip() and not jd_url.strip():
        raise HTTPException(400, "请提供 jd_text 或 jd_url")
    try:
        from backend.agents.jd_analyzer import analyze_jd, analyze_jd_from_url

        if jd_url.strip():
            jd = analyze_jd_from_url(jd_url.strip())
        else:
            jd = analyze_jd(jd_text.strip())

        return JSONResponse({
            "step": "analyze_jd",
            "status": "ok",
            "jd": jd.model_dump(exclude={"raw_text"}, exclude_none=True),
        })
    except Exception as e:
        return JSONResponse({"step": "analyze_jd", "status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════
# Step 3: ATS 评分
# ═══════════════════════════════════════════════════════════════════════

@router.post("/score-ats")
async def debug_score_ats(
    resume_pdf: UploadFile = File(..., description="简历 PDF"),
    jd_text: str = Form(default="", description="JD 文本"),
    jd_url: str = Form(default="", description="或 JD URL"),
):
    """上传简历 + JD，运行 简历解析 → JD分析 → ATS评分，返回三步结果。"""
    if not jd_text.strip() and not jd_url.strip():
        raise HTTPException(400, "请提供 jd_text 或 jd_url")

    tmp_path = _save_upload(resume_pdf)
    try:
        from backend.tools.pdf_parser import extract_text_from_pdf
        from backend.agents.resume_parser import parse_resume
        from backend.agents.jd_analyzer import analyze_jd, analyze_jd_from_url
        from backend.agents.ats_scorer import score_ats

        # Step 1
        raw = extract_text_from_pdf(str(tmp_path))
        resume = parse_resume(raw)

        # Step 2
        if jd_url.strip():
            jd = analyze_jd_from_url(jd_url.strip())
        else:
            jd = analyze_jd(jd_text.strip())

        # Step 3
        ats = score_ats(resume, jd)

        return JSONResponse({
            "step": "score_ats",
            "status": "ok",
            "resume": resume.model_dump(exclude_none=True),
            "jd": jd.model_dump(exclude={"raw_text"}, exclude_none=True),
            "ats": ats.model_dump(exclude_none=True),
        })
    except Exception as e:
        return JSONResponse({"step": "score_ats", "status": "error", "error": str(e)})
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ═══════════════════════════════════════════════════════════════════════
# Step 4: 简历改写
# ═══════════════════════════════════════════════════════════════════════

@router.post("/rewrite")
async def debug_rewrite(
    resume_pdf: UploadFile = File(..., description="简历 PDF"),
    jd_text: str = Form(default="", description="JD 文本"),
    jd_url: str = Form(default="", description="或 JD URL"),
):
    """上传简历 + JD，运行全流程到改写，返回改写结果。"""
    if not jd_text.strip() and not jd_url.strip():
        raise HTTPException(400, "请提供 jd_text 或 jd_url")

    tmp_path = _save_upload(resume_pdf)
    try:
        from backend.tools.pdf_parser import extract_text_from_pdf
        from backend.agents.resume_parser import parse_resume
        from backend.agents.jd_analyzer import analyze_jd, analyze_jd_from_url
        from backend.agents.ats_scorer import score_ats
        from backend.agents.rewrite_agent import rewrite_resume

        raw = extract_text_from_pdf(str(tmp_path))
        resume = parse_resume(raw)

        if jd_url.strip():
            jd = analyze_jd_from_url(jd_url.strip())
        else:
            jd = analyze_jd(jd_text.strip())

        ats = score_ats(resume, jd)
        rewritten = rewrite_resume(resume, jd, ats)

        return JSONResponse({
            "step": "rewrite",
            "status": "ok",
            "ats_score": ats.overall_score,
            "rewritten": rewritten.model_dump(exclude_none=True),
        })
    except Exception as e:
        return JSONResponse({"step": "rewrite", "status": "error", "error": str(e)})
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ═══════════════════════════════════════════════════════════════════════
# Step 5: 面试题生成
# ═══════════════════════════════════════════════════════════════════════

@router.post("/interview")
async def debug_interview(
    resume_pdf: UploadFile = File(..., description="简历 PDF"),
    jd_text: str = Form(default="", description="JD 文本"),
    jd_url: str = Form(default="", description="或 JD URL"),
):
    """上传简历 + JD，运行全流程到面试题，返回面试题结果。"""
    if not jd_text.strip() and not jd_url.strip():
        raise HTTPException(400, "请提供 jd_text 或 jd_url")

    tmp_path = _save_upload(resume_pdf)
    try:
        from backend.tools.pdf_parser import extract_text_from_pdf
        from backend.agents.resume_parser import parse_resume
        from backend.agents.jd_analyzer import analyze_jd, analyze_jd_from_url
        from backend.agents.ats_scorer import score_ats
        from backend.agents.interview_agent import generate_interview_questions

        raw = extract_text_from_pdf(str(tmp_path))
        resume = parse_resume(raw)

        if jd_url.strip():
            jd = analyze_jd_from_url(jd_url.strip())
        else:
            jd = analyze_jd(jd_text.strip())

        ats = score_ats(resume, jd)
        questions = generate_interview_questions(resume, jd, ats)

        return JSONResponse({
            "step": "interview",
            "status": "ok",
            "ats_score": ats.overall_score,
            "questions": questions.model_dump(exclude_none=True),
        })
    except Exception as e:
        return JSONResponse({"step": "interview", "status": "error", "error": str(e)})
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
