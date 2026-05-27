from pydantic import BaseModel, Field


class InterviewQuestion(BaseModel):
    question: str = Field(description="The interview question")
    category: str = Field(
        description="Category: behavioral, technical, situational, or follow-up"
    )
    difficulty: str = Field(description="Difficulty: easy, medium, or hard")
    focus_area: str = Field(
        description="What this question evaluates (e.g., 'Python proficiency', 'teamwork', 'system design')"
    )
    expected_topics: list[str] = Field(
        default_factory=list,
        description="Key topics the candidate should cover in their answer",
    )


class InterviewQuestions(BaseModel):
    behavioral_questions: list[InterviewQuestion] = Field(
        default_factory=list, description="Behavioral and soft-skill questions"
    )
    technical_questions: list[InterviewQuestion] = Field(
        default_factory=list, description="Technical and domain-specific questions"
    )
    situational_questions: list[InterviewQuestion] = Field(
        default_factory=list, description="Scenario-based and problem-solving questions"
    )
    gap_probing_questions: list[InterviewQuestion] = Field(
        default_factory=list,
        description="Questions targeting skill gaps identified in ATS analysis",
    )
    follow_up_strategy: str = Field(
        default="",
        description="Overall strategy for follow-up questions during the interview",
    )
