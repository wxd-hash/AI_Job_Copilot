"""Phase 3 Test — Rewrite Agent + Interview Agent.

Usage:
    python tests/test_phase3.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from backend.core.config import settings
from backend.core.logger import setup_logger

logger = setup_logger("test.phase3")

# ── Phase 2 outputs (simulated) ──────────────────────────────────────
# In production, these come from earlier pipeline stages.

SAMPLE_RESUME_JSON = {
    "contact": {
        "name": "Zhang Wei",
        "email": "zhangwei@example.com",
        "phone": "+86 138-0000-1234",
        "location": "Beijing, China",
    },
    "summary": (
        "Senior Python backend engineer with 5 years of experience building "
        "distributed systems and data pipelines. Strong in FastAPI, PostgreSQL, "
        "Docker, and AWS."
    ),
    "skills": [
        "Python", "FastAPI", "Django", "PostgreSQL", "MySQL", "Redis",
        "Docker", "Kubernetes", "AWS", "Git", "CI/CD", "REST API",
        "Microservices", "SQLAlchemy", "Pytest", "Linux", "Agile",
    ],
    "experience": [
        {
            "title": "Senior Backend Engineer",
            "company": "TechCorp Beijing",
            "start_date": "2022-03",
            "end_date": None,
            "highlights": [
                "Designed and built 12 microservices handling 50k req/s",
                "Led migration from monolith to Kubernetes-based architecture",
                "Reduced API latency by 40% through query optimization",
            ],
        },
        {
            "title": "Backend Developer",
            "company": "StartupXYZ",
            "start_date": "2019-07",
            "end_date": "2022-02",
            "highlights": [
                "Built REST APIs with FastAPI and PostgreSQL",
                "Implemented CI/CD pipelines with GitHub Actions",
                "Developed internal data pipeline processing 2TB daily",
            ],
        },
    ],
    "projects": [
        {
            "name": "Real-time Analytics Platform",
            "description": "Streaming analytics system using Kafka and Flink",
            "technologies": ["Python", "Kafka", "Flink", "PostgreSQL", "Docker"],
        },
    ],
    "education": [
        {
            "degree": "B.S. Computer Science",
            "institution": "Tsinghua University",
            "year": "2019",
        },
    ],
    "certifications": ["AWS Solutions Architect Associate"],
    "languages": ["Chinese (Native)", "English (Fluent)"],
}

SAMPLE_JD_JSON = {
    "role_title": "Senior Backend Engineer",
    "department": "AI Platform",
    "seniority_level": "Senior",
    "required_skills": [
        "Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes",
        "REST API design", "microservices architecture", "CI/CD pipelines",
    ],
    "preferred_skills": [
        "ML model serving", "Kafka", "RabbitMQ", "AWS", "GCP",
        "Prometheus", "Grafana", "MongoDB", "Cassandra",
        "open-source contributions",
    ],
    "keywords": [
        "Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes",
        "AWS", "Kafka", "Prometheus", "Grafana", "GitHub Actions",
    ],
    "years_of_experience": 5.0,
    "education_requirement": "Bachelor's degree",
}


# ── Test functions ────────────────────────────────────────────────────

def test_rewrite_agent(resume_json, jd_json, ats_json):
    print("\n" + "=" * 60)
    print("TEST 1: Resume Rewrite Agent")
    print("=" * 60)

    from backend.schemas.resume import Resume
    from backend.schemas.jd import JobDescription
    from backend.schemas.ats import ATSScore
    from backend.agents.rewrite_agent import rewrite_resume

    resume = Resume(**resume_json)
    jd = JobDescription(**jd_json)
    ats = ATSScore(**ats_json)

    result = rewrite_resume(resume, jd, ats)

    print(f"  Improved Bullets: {len(result.improved_bullets)}")
    for i, bullet in enumerate(result.improved_bullets):
        print(f"\n  --- Bullet {i+1} ({bullet.section}) ---")
        print(f"  Original:  {bullet.original[:120]}...")
        print(f"  Rewritten: {bullet.rewritten[:120]}...")
        print(f"  Keywords:  {bullet.added_keywords}")

    print(f"\n  Suggested Summary:")
    print(f"  {result.suggested_summary[:300]}...")

    print(f"\n  Skill Gap Plan: {len(result.skill_gap_plan)} items")
    for gap in result.skill_gap_plan[:4]:
        print(f"    [{gap.priority}] {gap.missing_skill}")
        print(f"      -> {gap.suggestion[:120]}...")

    print(f"\n  Keyword Additions: {result.keyword_additions}")

    # Validation
    assert len(result.improved_bullets) > 0, "must have improved bullets"
    assert result.suggested_summary, "must have suggested summary"
    assert len(result.skill_gap_plan) > 0, "must have gap plan"

    print("\n  Rewrite Agent [OK]")
    return result


def test_interview_agent(resume_json, jd_json, ats_json):
    print("\n" + "=" * 60)
    print("TEST 2: Interview Agent")
    print("=" * 60)

    from backend.schemas.resume import Resume
    from backend.schemas.jd import JobDescription
    from backend.schemas.ats import ATSScore
    from backend.agents.interview_agent import generate_interview_questions

    resume = Resume(**resume_json)
    jd = JobDescription(**jd_json)
    ats = ATSScore(**ats_json)

    result = generate_interview_questions(resume, jd, ats)

    def print_questions(title: str, questions):
        print(f"\n  [{title}] ({len(questions)} questions)")
        for i, q in enumerate(questions):
            print(f"  Q{i+1} [{q.difficulty}] {q.question}")
            print(f"       Focus: {q.focus_area}")
            print(f"       Topics: {', '.join(q.expected_topics[:3])}")

    print_questions("Behavioral", result.behavioral_questions)
    print_questions("Technical", result.technical_questions)
    print_questions("Situational", result.situational_questions)
    print_questions("Gap Probing", result.gap_probing_questions)

    print(f"\n  Follow-up Strategy:")
    print(f"  {result.follow_up_strategy}")

    # Validation
    assert len(result.behavioral_questions) >= 2, "need behavioral questions"
    assert len(result.technical_questions) >= 3, "need technical questions"
    assert len(result.gap_probing_questions) >= 1, "need gap probing"
    assert result.follow_up_strategy, "must have follow-up strategy"

    print("\n  Interview Agent [OK]")
    return result


def main():
    print("\n" + "#" * 60)
    print("  PHASE 3 TEST SUITE — Rewrite + Interview Agents")
    print("#" * 60)

    # Build ATS data using the Phase 2 output as reference
    ats_json = {
        "overall_score": 85,
        "matched_skills": [
            {"skill": "Python", "match_type": "exact"},
            {"skill": "FastAPI", "match_type": "exact"},
            {"skill": "PostgreSQL", "match_type": "exact"},
            {"skill": "Docker", "match_type": "exact"},
            {"skill": "Kubernetes", "match_type": "exact"},
            {"skill": "REST API", "match_type": "related"},
            {"skill": "Microservices", "match_type": "related"},
            {"skill": "CI/CD", "match_type": "exact"},
            {"skill": "AWS", "match_type": "exact"},
            {"skill": "Kafka", "match_type": "exact"},
        ],
        "missing_skills": [
            {"skill": "ML model serving", "importance": "preferred"},
            {"skill": "RabbitMQ", "importance": "preferred"},
            {"skill": "GCP", "importance": "preferred"},
            {"skill": "Prometheus", "importance": "preferred"},
            {"skill": "Grafana", "importance": "preferred"},
            {"skill": "MongoDB", "importance": "preferred"},
            {"skill": "Cassandra", "importance": "preferred"},
            {"skill": "open-source contributions", "importance": "preferred"},
        ],
        "skill_breakdown": {
            "technical_match": 90.0,
            "experience_match": 90.0,
            "education_match": 100.0,
            "keyword_match": 70.0,
        },
        "reasoning": (
            "Strong match on core backend skills and experience. "
            "Missing several preferred skills in ML serving and monitoring."
        ),
        "recommendations": [
            "Highlight any experience with monitoring tools",
            "Add open-source contributions if applicable",
        ],
    }

    # Run tests
    rewrite = test_rewrite_agent(SAMPLE_RESUME_JSON, SAMPLE_JD_JSON, ats_json)
    interview = test_interview_agent(SAMPLE_RESUME_JSON, SAMPLE_JD_JSON, ats_json)

    print("\n" + "#" * 60)
    print("  PHASE 3 COMPLETE [OK]")
    print("#" * 60)

    # Save output
    output_path = os.path.join(os.path.dirname(__file__), "phase3_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "rewrite": rewrite.model_dump(exclude_none=True),
            "interview": interview.model_dump(exclude_none=True),
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Full output saved to: {output_path}")


if __name__ == "__main__":
    main()
