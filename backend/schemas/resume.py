from pydantic import BaseModel, Field
from typing import Optional


class Project(BaseModel):
    name: str = Field(description="Project name")
    description: str = Field(description="Brief description of the project")
    technologies: list[str] = Field(
        default_factory=list, description="Technologies used"
    )


class Experience(BaseModel):
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    start_date: Optional[str] = Field(default=None, description="Start date")
    end_date: Optional[str] = Field(default=None, description="End date")
    highlights: list[str] = Field(
        default_factory=list, description="Key achievements and responsibilities"
    )


class Education(BaseModel):
    degree: str = Field(description="Degree earned")
    institution: str = Field(description="Institution name")
    year: Optional[str] = Field(default=None, description="Graduation year")
    gpa: Optional[str] = Field(default=None, description="GPA if available")


class ContactInfo(BaseModel):
    name: Optional[str] = Field(default=None, description="Full name")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="Location")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn URL")
    github: Optional[str] = Field(default=None, description="GitHub URL")


class Resume(BaseModel):
    contact: Optional[ContactInfo] = Field(
        default=None, description="Contact information"
    )
    summary: Optional[str] = Field(
        default=None, description="Professional summary"
    )
    skills: list[str] = Field(
        default_factory=list, description="Technical and soft skills"
    )
    experience: list[Experience] = Field(
        default_factory=list, description="Work experience"
    )
    projects: list[Project] = Field(
        default_factory=list, description="Projects"
    )
    education: list[Education] = Field(
        default_factory=list, description="Education history"
    )
    certifications: list[str] = Field(
        default_factory=list, description="Certifications"
    )
    languages: list[str] = Field(
        default_factory=list, description="Languages spoken"
    )
