from pydantic import BaseModel, Field


class MatchedSkill(BaseModel):
    skill: str = Field(description="The skill name")
    match_type: str = Field(
        description="Match type: exact, related, or inferred"
    )


class MissingSkill(BaseModel):
    skill: str = Field(description="The skill name")
    importance: str = Field(
        description="Whether this is a required or preferred skill"
    )


class SkillBreakdown(BaseModel):
    technical_match: float = Field(
        ge=0, le=100, description="Technical skills match percentage"
    )
    experience_match: float = Field(
        ge=0, le=100, description="Experience/role match percentage"
    )
    education_match: float = Field(
        ge=0, le=100, description="Education match percentage"
    )
    keyword_match: float = Field(
        ge=0, le=100, description="Keyword density match percentage"
    )


class ATSScore(BaseModel):
    overall_score: int = Field(
        ge=0, le=100, description="Overall ATS match score (0-100)"
    )
    matched_skills: list[MatchedSkill] = Field(
        default_factory=list, description="Skills that matched"
    )
    missing_skills: list[MissingSkill] = Field(
        default_factory=list, description="Skills missing from resume"
    )
    skill_breakdown: SkillBreakdown = Field(
        description="Breakdown by category"
    )
    reasoning: str = Field(
        description="Detailed reasoning explaining the score"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations to improve the match",
    )
