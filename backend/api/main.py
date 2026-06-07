"""
FastAPI application for the Multi-Agent AI Job Copilot.

Endpoints:
    GET  /              API info
    GET  /health        Health check
    POST /analyze       Upload resume PDF + JD, run full pipeline
"""

import os
import uuid
import tempfile
import traceback
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.logger import setup_logger
from backend.core.database import save_analysis, list_analyses, get_analysis, delete_analysis
from backend.workflows.graph import run_pipeline
from backend.workflows.progress import (
    create_session, get_progress, get_result, set_result, cleanup_session, STEP_LABELS
)
from backend.api.debug_routes import router as debug_router

logger = setup_logger("api")

app = FastAPI(
    title="AI 求职助手",
    description="基于通义千问 (DashScope) 的多智能体 AI 简历分析系统",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(debug_router)


@app.on_event("startup")
async def startup():
    settings.validate()
    logger.info("AI Job Copilot API started — model=%s", settings.MODEL_NAME)


@app.get("/")
async def root():
    return {
        "service": "AI 求职助手",
        "version": "0.1.0",
        "model": settings.MODEL_NAME,
        "endpoints": {
            "health": "/health",
            "analyze": "POST /analyze (简历PDF + 职位描述)",
            "debug": "/debug/* (5个调试端点)",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "model": settings.MODEL_NAME}


# ═══════════════════════════════════════════════════════════
# 历史记录
# ═══════════════════════════════════════════════════════════

@app.get("/history")
async def list_history(limit: int = 20):
    """列出所有历史分析记录（按时间倒序）。"""
    return {"analyses": list_analyses(limit)}


@app.get("/history/{analysis_id}")
async def get_history(analysis_id: str):
    """获取一次历史分析的完整结果。"""
    result = get_analysis(analysis_id)
    if not result:
        raise HTTPException(404, "记录不存在")
    return result


@app.delete("/history/{analysis_id}")
async def delete_history(analysis_id: str):
    """删除一次历史分析。"""
    if not delete_analysis(analysis_id):
        raise HTTPException(404, "记录不存在")
    return {"status": "deleted"}


@app.get("/progress/{session_id}")
async def progress(session_id: str):
    """查询管道执行进度。"""
    prog = get_progress(session_id)
    if not prog:
        raise HTTPException(404, "会话不存在或已过期")
    return {
        "session_id": session_id,
        "completed": prog["completed"],
        "current": prog["current"],
        "total_steps": 5,
        "step_labels": STEP_LABELS,
    }


@app.post("/analyze")
async def analyze(
    resume_pdf: UploadFile = File(..., description="Resume PDF file"),
    jd_text: str = Form(default="", description="Job description text"),
    jd_url: str = Form(default="", description="Job posting URL"),
) -> JSONResponse:
    """上传简历 PDF + JD，启动后台分析，返回 session_id 供轮询进度。"""
    if not resume_pdf.filename or not resume_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "只接受 .pdf 文件")

    if not jd_text.strip() and not jd_url.strip():
        raise HTTPException(400, "请提供 JD 文本或链接")

    content = await resume_pdf.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "PDF 文件超过 10MB")

    tmp_dir = Path(tempfile.gettempdir()) / "ai_job_copilot"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4().hex}_{resume_pdf.filename}"
    tmp_path.write_bytes(content)
    logger.info("Saved uploaded PDF: %s (%d bytes)", tmp_path.name, len(content))

    session_id = create_session()

    def _run():
        try:
            state = run_pipeline(
                pdf_path=str(tmp_path),
                jd_text=jd_text.strip(),
                jd_url=jd_url.strip(),
                session_id=session_id,
            )
            error = state.get("error", "")
            stage = state.get("current_stage", "unknown")
            report = state.get("final_report", {})
            if error:
                set_result(session_id, {
                    "status": "error", "stage": stage,
                    "error": error,
                    "partial_report": report if report else None,
                })
            else:
                # 保存到 SQLite
                try:
                    save_analysis(
                        session_id=session_id,
                        report=report,
                        jd_text=jd_text.strip(),
                        resume_snapshot=state.get("resume", {}),
                    )
                except Exception as e:
                    logger.warning("Failed to save analysis: %s", e)

                set_result(session_id, {
                    "status": "completed", "report": report,
                })
        except Exception as e:
            logger.error("Background pipeline crashed: %s", e)
            traceback.print_exc()
            set_result(session_id, {"status": "error", "error": f"系统错误: {e}"})
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    threading.Thread(target=_run, daemon=True).start()

    return JSONResponse(content={
        "status": "processing",
        "session_id": session_id,
    })


@app.get("/result/{session_id}")
async def get_analysis_result(session_id: str):
    """获取后台分析结果（完成后自动清理）。"""
    result = get_result(session_id)
    if not result:
        prog = get_progress(session_id)
        if not prog:
            raise HTTPException(404, "会话不存在或已过期")
        return JSONResponse(content={
            "status": "processing",
            "completed": prog["completed"],
            "total": 5,
        })
    cleanup_session(session_id)
    return JSONResponse(content=result)
