from pydantic import BaseModel, Field


class RewrittenBullet(BaseModel):
    original: str = Field(description="Original bullet point from the resume")
    rewritten: str = Field(description="ATS-optimized version of the bullet")
    added_keywords: list[str] = Field(
        default_factory=list, description="Keywords added to this bullet"
    )
    section: str = Field(
        description="Which resume section this belongs to: experience, skills, summary, projects"
    )


class SkillGapAction(BaseModel):
    missing_skill: str = Field(description="The skill that is missing")
    suggestion: str = Field(
        description="How to address this gap (learn, reframe, or highlight adjacent experience)"
    )
    priority: str = Field(description="Priority level: high, medium, low")


class RewrittenResume(BaseModel):
    improved_bullets: list[RewrittenBullet] = Field(
        default_factory=list,
        description="ATS-optimized bullet points with before/after",
    )
    suggested_summary: str = Field(
        default="",
        description="Rewritten professional summary incorporating JD keywords",
    )
    skill_gap_plan: list[SkillGapAction] = Field(
        default_factory=list,
        description="Actionable plan for addressing each missing skill",
    )
    keyword_additions: list[str] = Field(
        default_factory=list,
        description="JD keywords that were added across the resume",
    )
