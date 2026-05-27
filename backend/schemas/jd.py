from pydantic import BaseModel, Field, field_validator
from typing import Optional


class JobDescription(BaseModel):
    role_title: str = Field(
        default="",
        description="Job title / role name. Defaults to empty string if unparseable.",
    )
    department: Optional[str] = Field(
        default=None, description="Department or team"
    )
    seniority_level: str = Field(
        default="",
        description="Seniority level: Intern, Junior, Mid-Level, Senior, Lead, Manager, Director. Defaults to empty string if unparseable.",
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description="Must-have technical and soft skills",
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        description="Nice-to-have skills that give candidates an edge",
    )
    responsibilities: list[str] = Field(
        default_factory=list, description="Key responsibilities"
    )
    qualifications: list[str] = Field(
        default_factory=list, description="Required qualifications"
    )
    education_requirement: Optional[str] = Field(
        default=None, description="Minimum education required"
    )
    years_of_experience: Optional[float] = Field(
        default=None, description="Required years of experience"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Important ATS keywords extracted from the JD",
    )
    industry: Optional[str] = Field(
        default=None, description="Industry domain"
    )
    raw_text: Optional[str] = Field(
        default=None, description="Original JD text", exclude=True
    )

    @field_validator("role_title", "seniority_level", mode="before")
    @classmethod
    def _coerce_none_to_empty(cls, v: str | None) -> str:
        return v if v is not None else ""
