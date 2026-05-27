"""
LangGraph workflow orchestrating the full multi-agent pipeline.

Graph topology (two levels of parallelism):
              START
              ┌───┴───┐
              ↓       ↓
        parse_resume  analyze_jd   ← parallel L1
              └───┬───┘
                  ↓
              score_ats
              ┌───┴───┐
              ↓       ↓
           rewrite  interview      ← parallel L2
              └───┬───┘
                  ↓
          aggregate_report
                  ↓
                 END
"""

import time

from langgraph.graph import StateGraph, START, END

from backend.workflows.state import PipelineState
from backend.workflows.progress import update_progress
from backend.core.logger import setup_logger
from backend.schemas.report import FinalReport, PipelineMetadata
from backend.tools.pdf_parser import extract_text_from_pdf

logger = setup_logger("workflow.graph")


# ═══════════════════════════════════════════════════════════════════════
# Node implementations
# ═══════════════════════════════════════════════════════════════════════

def _parse_resume_node(state: PipelineState) -> dict:
    logger.info("[node] parse_resume started")
    t0 = time.perf_counter()

    try:
        from backend.agents.resume_parser import parse_resume

        pdf_path = state.get("pdf_path", "")
        if not pdf_path:
            raise ValueError("pdf_path is required")

        raw_text = extract_text_from_pdf(pdf_path)
        resume = parse_resume(raw_text)

        elapsed = time.perf_counter() - t0
        logger.info("[node] parse_resume completed in %.2fs", elapsed)
        update_progress(state.get("session_id", ""), "resume_parsed")

        return {
            "resume_raw_text": raw_text,
            "resume": resume.model_dump(exclude_none=True),
            "current_stage": "resume_parsed",
            "resume_parser_duration_s": elapsed,
        }
    except Exception as e:
        logger.error("[node] parse_resume failed: %s", e)
        return {"error": f"简历解析失败: {e}", "current_stage": "error"}


def _analyze_jd_node(state: PipelineState) -> dict:
    logger.info("[node] analyze_jd started")
    t0 = time.perf_counter()

    try:
        from backend.agents.jd_analyzer import analyze_jd, analyze_jd_from_url

        jd_url = state.get("jd_url", "")
        jd_text = state.get("jd_text", "")

        if jd_url:
            jd = analyze_jd_from_url(jd_url)
        elif jd_text:
            jd = analyze_jd(jd_text)
        else:
            raise ValueError("需要提供 jd_text 或 jd_url")

        elapsed = time.perf_counter() - t0
        logger.info("[node] analyze_jd completed in %.2fs", elapsed)
        update_progress(state.get("session_id", ""), "jd_analyzed")

        return {
            "jd": jd.model_dump(exclude={"raw_text"}, exclude_none=True),
            "current_stage": "jd_analyzed",
            "jd_analyzer_duration_s": elapsed,
        }
    except Exception as e:
        logger.error("[node] analyze_jd failed: %s", e)
        return {"error": f"JD分析失败: {e}", "current_stage": "error"}


def _score_ats_node(state: PipelineState) -> dict:
    logger.info("[node] score_ats started")
    t0 = time.perf_counter()

    try:
        from backend.schemas.resume import Resume
        from backend.schemas.jd import JobDescription
        from backend.agents.ats_scorer import score_ats

        resume = Resume(**state["resume"])
        jd = JobDescription(**state["jd"])
        ats = score_ats(resume, jd)

        elapsed = time.perf_counter() - t0
        logger.info("[node] score_ats completed in %.2fs", elapsed)
        update_progress(state.get("session_id", ""), "ats_scored")

        return {
            "ats": ats.model_dump(exclude_none=True),
            "current_stage": "ats_scored",
            "ats_scorer_duration_s": elapsed,
        }
    except Exception as e:
        logger.error("[node] score_ats failed: %s", e)
        return {"error": f"ATS评分失败: {e}", "current_stage": "error"}


def _rewrite_node(state: PipelineState) -> dict:
    logger.info("[node] rewrite started (parallel)")
    t0 = time.perf_counter()

    try:
        from backend.schemas.resume import Resume
        from backend.schemas.jd import JobDescription
        from backend.schemas.ats import ATSScore
        from backend.agents.rewrite_agent import rewrite_resume

        resume = Resume(**state["resume"])
        jd = JobDescription(**state["jd"])
        ats = ATSScore(**state["ats"])
        result = rewrite_resume(resume, jd, ats)

        elapsed = time.perf_counter() - t0
        logger.info("[node] rewrite completed in %.2fs", elapsed)
        update_progress(state.get("session_id", ""), "rewrite_done")

        return {
            "rewritten_resume": result.model_dump(exclude_none=True),
            "current_stage": "rewrite_done",
            "rewrite_agent_duration_s": elapsed,
        }
    except Exception as e:
        logger.error("[node] rewrite failed: %s", e)
        return {"error": f"简历改写失败: {e}", "current_stage": "rewrite_error"}


def _interview_node(state: PipelineState) -> dict:
    logger.info("[node] interview started (parallel)")
    t0 = time.perf_counter()

    try:
        from backend.schemas.resume import Resume
        from backend.schemas.jd import JobDescription
        from backend.schemas.ats import ATSScore
        from backend.agents.interview_agent import generate_interview_questions

        resume = Resume(**state["resume"])
        jd = JobDescription(**state["jd"])
        ats = ATSScore(**state["ats"])
        result = generate_interview_questions(resume, jd, ats)

        elapsed = time.perf_counter() - t0
        logger.info("[node] interview completed in %.2fs", elapsed)
        update_progress(state.get("session_id", ""), "interview_done")

        return {
            "interview_questions": result.model_dump(exclude_none=True),
            "current_stage": "interview_done",
            "interview_agent_duration_s": elapsed,
        }
    except Exception as e:
        logger.error("[node] interview failed: %s", e)
        return {"error": f"面试题生成失败: {e}", "current_stage": "interview_error"}


def _aggregate_report_node(state: PipelineState) -> dict:
    logger.info("[node] aggregate_report started")

    try:
        from datetime import datetime, timezone

        metadata = PipelineMetadata(
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            resume_parser_duration_s=state.get("resume_parser_duration_s"),
            jd_analyzer_duration_s=state.get("jd_analyzer_duration_s"),
            ats_scorer_duration_s=state.get("ats_scorer_duration_s"),
            rewrite_agent_duration_s=state.get("rewrite_agent_duration_s"),
            interview_agent_duration_s=state.get("interview_agent_duration_s"),
        )

        resume = state.get("resume", {})
        ats = state.get("ats", {})
        rewritten = state.get("rewritten_resume", {})
        interview = state.get("interview_questions", {})

        top_matched = [
            m["skill"] for m in ats.get("matched_skills", [])[:5]
        ]

        critical_missing = [
            m["skill"]
            for m in ats.get("missing_skills", [])
            if m.get("importance") == "required"
        ]

        rewrite_highlights = []
        for b in rewritten.get("improved_bullets", []):
            rewrite_highlights.append({
                "section": b.get("section", ""),
                "original": b.get("original", ""),
                "rewritten": b.get("rewritten", ""),
                "added_keywords": b.get("added_keywords", []),
            })

        interview_preview = []
        for q in interview.get("technical_questions", []):
            interview_preview.append({
                "question": q.get("question", ""),
                "difficulty": q.get("difficulty", ""),
                "focus_area": q.get("focus_area", ""),
            })

        report = FinalReport(
            metadata=metadata,
            contact=resume.get("contact"),
            session_id=state.get("session_id", ""),
            ats_summary={
                "overall_score": ats.get("overall_score"),
                "technical_match": ats.get("skill_breakdown", {}).get("technical_match"),
                "experience_match": ats.get("skill_breakdown", {}).get("experience_match"),
                "education_match": ats.get("skill_breakdown", {}).get("education_match"),
                "keyword_match": ats.get("skill_breakdown", {}).get("keyword_match"),
                "reasoning": ats.get("reasoning"),
            },
            top_matched_skills=top_matched,
            critical_missing_skills=critical_missing,
            rewrite_highlights=rewrite_highlights,
            interview_preview=interview_preview,
            recommendations=ats.get("recommendations", []),
            rewritten_resume=rewritten if rewritten else None,
            interview_questions=interview if interview else None,
        )

        logger.info("[node] aggregate_report completed")
        return {
            "final_report": report.model_dump(exclude_none=True),
            "current_stage": "completed",
        }
    except Exception as e:
        logger.error("[node] aggregate_report failed: %s", e)
        return {"error": f"报告聚合失败: {e}", "current_stage": "error"}


# ═══════════════════════════════════════════════════════════════════════
# Routing
# ═══════════════════════════════════════════════════════════════════════

def _route_on_error(state: PipelineState) -> str:
    if state.get("error"):
        return "aggregate_report"
    return "continue"


# ═══════════════════════════════════════════════════════════════════════
# Graph builder
# ═══════════════════════════════════════════════════════════════════════

def build_pipeline_graph() -> StateGraph:
    """Build and compile the LangGraph pipeline with parallel fan-out."""

    graph = StateGraph(PipelineState)

    graph.add_node("parse_resume", _parse_resume_node)
    graph.add_node("analyze_jd", _analyze_jd_node)
    graph.add_node("score_ats", _score_ats_node)
    graph.add_node("rewrite", _rewrite_node)
    graph.add_node("interview", _interview_node)
    graph.add_node("aggregate_report", _aggregate_report_node)

    # START → parse_resume AND analyze_jd in parallel
    graph.add_edge(START, "parse_resume")
    graph.add_edge(START, "analyze_jd")

    # Both converge at score_ats (or skip to report on error)
    graph.add_conditional_edges("parse_resume", _route_on_error, {
        "continue": "score_ats",
        "aggregate_report": "aggregate_report",
    })
    graph.add_conditional_edges("analyze_jd", _route_on_error, {
        "continue": "score_ats",
        "aggregate_report": "aggregate_report",
    })

    # score_ats → FAN OUT to rewrite AND interview (two edges = parallel)
    graph.add_edge("score_ats", "rewrite")
    graph.add_edge("score_ats", "interview")

    # Both parallel branches converge at aggregate_report
    graph.add_edge("rewrite", "aggregate_report")
    graph.add_edge("interview", "aggregate_report")

    # aggregate_report → END
    graph.add_edge("aggregate_report", END)

    compiled = graph.compile()
    logger.info("Pipeline graph compiled (parallel mode)")
    return compiled


# ── Singleton ─────────────────────────────────────────────────────────

_pipeline = None


def get_pipeline() -> StateGraph:
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline_graph()
    return _pipeline


def run_pipeline(
    pdf_path: str = "",
    jd_text: str = "",
    jd_url: str = "",
    session_id: str = "",
) -> PipelineState:
    """Run the full multi-agent pipeline and return the final state."""
    import traceback

    pipeline = get_pipeline()
    initial_state: PipelineState = {
        "pdf_path": pdf_path,
        "jd_text": jd_text,
        "jd_url": jd_url,
        "session_id": session_id,
        "current_stage": "initialized",
    }
    logger.info("Starting pipeline: pdf=%s, jd_text_len=%d, jd_url=%s",
                 pdf_path, len(jd_text), jd_url)

    try:
        final_state = pipeline.invoke(initial_state)
    except Exception as e:
        logger.error("Pipeline invoke crashed: %s", e)
        traceback.print_exc()
        return {
            "error": f"Pipeline crashed: {e}",
            "current_stage": "crashed",
        }

    logger.info("Pipeline completed with stage=%s", final_state.get("current_stage"))
    return final_state
