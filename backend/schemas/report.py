from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class PipelineMetadata(BaseModel):
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    resume_parser_duration_s: Optional[float] = None
    jd_analyzer_duration_s: Optional[float] = None
    ats_scorer_duration_s: Optional[float] = None
    rewrite_agent_duration_s: Optional[float] = None
    interview_agent_duration_s: Optional[float] = None


class FinalReport(BaseModel):
    metadata: PipelineMetadata = Field(default_factory=PipelineMetadata)
    contact: Optional[dict] = None
    ats_summary: Optional[dict] = None
    top_matched_skills: list[str] = Field(default_factory=list)
    critical_missing_skills: list[str] = Field(default_factory=list)
    rewrite_highlights: list[dict] = Field(default_factory=list)
    interview_preview: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    # 完整数据（前端展开用）
    rewritten_resume: Optional[dict] = None
    interview_questions: Optional[dict] = None
    session_id: Optional[str] = None
