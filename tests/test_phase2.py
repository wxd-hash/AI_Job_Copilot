"""Phase 2 Test — JD Analyzer + ATS Scoring Agent.

Usage:
    python tests/test_phase2.py
    python tests/test_phase2.py --url "https://example.com/job-posting"
    python tests/test_phase2.py --jd "Paste JD text here"
"""

import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from backend.core.config import settings
from backend.core.logger import setup_logger

logger = setup_logger("test.phase2")

# ── Sample data for testing ──────────────────────────────────────────

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

SAMPLE_JD_TEXT = """
Senior Backend Engineer - AI Platform

About the Role:
We are looking for a Senior Backend Engineer to join our AI Platform team.
You will build and scale the infrastructure that powers our machine learning
models in production.

Responsibilities:
- Design and implement scalable microservices and APIs
- Build and maintain data pipelines for ML model training
- Optimize database performance and query patterns
- Collaborate with ML engineers to deploy models to production
- Implement monitoring, alerting, and observability for production systems
- Mentor junior engineers and conduct code reviews

Required Qualifications:
- 5+ years of backend development experience
- Strong proficiency in Python
- Experience with FastAPI or similar async Python frameworks
- Deep knowledge of PostgreSQL and database optimization
- Experience with Docker and Kubernetes
- Strong understanding of REST API design and microservices architecture
- Experience with CI/CD pipelines
- Bachelor's degree in Computer Science or related field

Preferred Qualifications:
- Experience with ML model serving (TensorFlow Serving, Triton, etc.)
- Knowledge of message queues (Kafka, RabbitMQ)
- Experience with AWS or GCP
- Familiarity with monitoring tools (Prometheus, Grafana)
- Experience with NoSQL databases (MongoDB, Cassandra)
- Contributions to open-source projects

Tech Stack: Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, AWS,
Kafka, Prometheus, Grafana, GitHub Actions
"""


# ── Test functions ────────────────────────────────────────────────────

def test_config():
    print("\n" + "=" * 60)
    print("TEST 1: Configuration Loading")
    print("=" * 60)
    settings.validate()
    print(f"  MODEL_NAME:         {settings.MODEL_NAME}")
    print(f"  MODEL_NAME_COMPLEX: {settings.MODEL_NAME_COMPLEX}")
    print("  Config [OK]")


def test_jd_analyzer(jd_text: str):
    print("\n" + "=" * 60)
    print("TEST 2: JD Analyzer Agent")
    print("=" * 60)

    from backend.agents.jd_analyzer import analyze_jd

    jd = analyze_jd(jd_text)

    print(f"  Role:             {jd.role_title}")
    print(f"  Seniority:        {jd.seniority_level}")
    print(f"  Department:       {jd.department or 'N/A'}")
    print(f"  Required skills:  {len(jd.required_skills)} -> {jd.required_skills}")
    print(f"  Preferred skills: {len(jd.preferred_skills)} -> {jd.preferred_skills}")
    print(f"  Keywords:         {jd.keywords}")
    print(f"  Years experience: {jd.years_of_experience}")
    print(f"  Education:        {jd.education_requirement or 'N/A'}")

    # Validate
    assert jd.role_title, "role_title must not be empty"
    assert jd.seniority_level, "seniority_level must not be empty"
    assert len(jd.required_skills) > 0, "must have required_skills"
    print("\n  JD Analyzer [OK]")
    return jd


def test_ats_scorer(resume_json: dict, jd_obj):
    print("\n" + "=" * 60)
    print("TEST 3: ATS Scoring Agent")
    print("=" * 60)

    from backend.schemas.resume import Resume
    from backend.agents.ats_scorer import score_ats

    resume = Resume(**resume_json)
    result = score_ats(resume, jd_obj)

    print(f"  Overall Score:    {result.overall_score}/100")
    print(f"  Technical Match:  {result.skill_breakdown.technical_match}%")
    print(f"  Experience Match: {result.skill_breakdown.experience_match}%")
    print(f"  Education Match:  {result.skill_breakdown.education_match}%")
    print(f"  Keyword Match:    {result.skill_breakdown.keyword_match}%")
    print(f"  Matched Skills:   {len(result.matched_skills)}")
    for ms in result.matched_skills[:5]:
        print(f"    + {ms.skill} ({ms.match_type})")
    print(f"  Missing Skills:   {len(result.missing_skills)}")
    for ms in result.missing_skills:
        print(f"    - {ms.skill} ({ms.importance})")
    print(f"  Reasoning:        {result.reasoning[:200]}...")
    print(f"  Recommendations:  {len(result.recommendations)} items")
    for r in result.recommendations[:3]:
        print(f"    * {r}")

    # Validate
    assert 0 <= result.overall_score <= 100, "score must be 0-100"
    assert result.reasoning, "must have reasoning"
    assert len(result.recommendations) > 0, "must have recommendations"

    print("\n  ATS Scorer [OK]")
    return result


def test_jd_from_url(url: str):
    print("\n" + "=" * 60)
    print(f"TEST 2b: JD Analyzer from URL")
    print("=" * 60)
    print(f"  URL: {url}")

    from backend.agents.jd_analyzer import analyze_jd_from_url

    jd = analyze_jd_from_url(url)
    print(f"  Role: {jd.role_title}")
    print(f"  JD from URL [OK]")
    return jd


def main():
    parser = argparse.ArgumentParser(description="Phase 2 Test Suite")
    parser.add_argument("--url", type=str, help="URL of a job posting")
    parser.add_argument("--jd", type=str, help="Raw JD text (or use built-in sample)")
    args = parser.parse_args()

    print("\n" + "#" * 60)
    print("  PHASE 2 TEST SUITE — JD Analyzer + ATS Scorer")
    print("#" * 60)

    test_config()

    # Determine JD source
    if args.url:
        jd = test_jd_from_url(args.url)
    else:
        jd_text = args.jd if args.jd else SAMPLE_JD_TEXT
        if not args.jd:
            print("\n  (Using built-in sample JD — pass --jd or --url for custom)")
        jd = test_jd_analyzer(jd_text)

    # Run ATS scorer
    result = test_ats_scorer(SAMPLE_RESUME_JSON, jd)

    print("\n" + "#" * 60)
    print("  PHASE 2 COMPLETE [OK]")
    print("#" * 60)

    # Save full result for inspection
    output_path = os.path.join(
        os.path.dirname(__file__), "phase2_output.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "jd": jd.model_dump(exclude={"raw_text"}, exclude_none=True),
            "ats": result.model_dump(exclude_none=True),
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Full output saved to: {output_path}")


if __name__ == "__main__":
    main()
