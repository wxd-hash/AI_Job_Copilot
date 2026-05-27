from typing import TypedDict, Annotated, Any


def _reduce_error(current: str, update: str) -> str:
    """Keep the first error encountered, don't overwrite."""
    return current if current else update


def _reduce_stage(current: str, update: str) -> str:
    """Take the latest non-empty stage."""
    return update if update else current


class PipelineState(TypedDict, total=False):
    # ── Input ──
    pdf_path: str
    jd_text: str
    jd_url: str
    session_id: str

    # ── Intermediate ──
    resume_raw_text: str
    resume: dict[str, Any]
    jd: dict[str, Any]
    ats: dict[str, Any]
    rewritten_resume: dict[str, Any]
    interview_questions: dict[str, Any]
    final_report: dict[str, Any]

    # ── Timing ──
    resume_parser_duration_s: float
    jd_analyzer_duration_s: float
    ats_scorer_duration_s: float
    rewrite_agent_duration_s: float
    interview_agent_duration_s: float

    # ── Control (Annotated for parallel write safety) ──
    error: Annotated[str, _reduce_error]
    current_stage: Annotated[str, _reduce_stage]
