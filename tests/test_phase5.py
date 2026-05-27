"""Phase 5 Test — FastAPI Endpoints.

Usage:
    python tests/test_phase5.py
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from backend.core.logger import setup_logger
logger = setup_logger("test.phase5")

SAMPLE_JD_TEXT = """
Senior Backend Engineer - AI Platform

Responsibilities:
- Design and implement scalable microservices and APIs
- Build and maintain data pipelines for ML model training
- Optimize database performance and query patterns

Required Qualifications:
- 5+ years of backend development experience
- Strong proficiency in Python, FastAPI, PostgreSQL
- Experience with Docker and Kubernetes
- Experience with CI/CD pipelines
- Bachelor's degree in Computer Science

Preferred Qualifications:
- Experience with ML model serving
- Knowledge of Kafka, RabbitMQ
- Experience with AWS or GCP
- Familiarity with Prometheus, Grafana
"""


def create_test_pdf(output_path: str) -> str:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    resume_text = (
        "ZHANG WEI\n"
        "Senior Backend Engineer\n"
        "zhangwei@example.com | +86 138-0000-1234 | Beijing, China\n\n"
        "SKILLS\n"
        "Python, FastAPI, Django, PostgreSQL, MySQL, Redis, Docker, Kubernetes, "
        "AWS, Git, CI/CD, REST API, Microservices, SQLAlchemy, Pytest, Linux\n\n"
        "WORK EXPERIENCE\n"
        "Senior Backend Engineer | TechCorp Beijing | 2022-03 to Present\n"
        "- Designed and built 12 microservices handling 50k req/s\n"
        "- Led migration from monolith to Kubernetes-based architecture\n"
        "- Reduced API latency by 40% through query optimization\n\n"
        "Backend Developer | StartupXYZ | 2019-07 to 2022-02\n"
        "- Built REST APIs with FastAPI and PostgreSQL\n"
        "- Implemented CI/CD pipelines with GitHub Actions\n"
        "- Developed internal data pipeline processing 2TB daily\n\n"
        "EDUCATION\n"
        "B.S. Computer Science | Tsinghua University | 2019\n\n"
        "CERTIFICATIONS\n"
        "AWS Solutions Architect Associate"
    )
    page.insert_textbox(fitz.Rect(50, 50, 545, 792), resume_text,
                         fontsize=10, fontname="helv")
    doc.save(output_path)
    doc.close()
    return output_path


def test_health():
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    import httpx
    r = httpx.get("http://localhost:8000/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    print(f"  Status: {data['status']}, Model: {data['model']}")
    print("  Health Check [OK]")


def test_analyze():
    print("\n" + "=" * 60)
    print("TEST 2: POST /analyze (Full Pipeline)")
    print("=" * 60)

    import httpx

    # Create test PDF
    tmp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmp_dir, "test_resume.pdf")
    create_test_pdf(pdf_path)
    print(f"  Test PDF: {pdf_path}")

    # Send request
    with open(pdf_path, "rb") as f:
        files = {"resume_pdf": ("resume.pdf", f, "application/pdf")}
        data = {"jd_text": SAMPLE_JD_TEXT}
        print("  Sending request (this will take ~3 minutes)...")
        print("  Waiting", end="", flush=True)

        # Use longer timeout since pipeline takes ~3 min
        r = httpx.post(
            "http://localhost:8000/analyze",
            files=files,
            data=data,
            timeout=300,  # 5 minutes
        )

    print()
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:500]}"

    result = r.json()
    assert result["status"] == "completed"
    report = result["report"]

    # Print summary
    ats = report.get("ats_summary", {})
    print(f"  ATS Score:     {ats.get('overall_score')}/100")
    print(f"  Tech Match:    {ats.get('technical_match')}%")
    print(f"  Exp Match:     {ats.get('experience_match')}%")
    print(f"  Top Skills:    {report.get('top_matched_skills', [])}")
    print(f"  Rewrite Items: {len(report.get('rewrite_highlights', []))}")
    print(f"  Interview Qs:  {len(report.get('interview_preview', []))}")
    print(f"  Recommendations: {len(report.get('recommendations', []))}")

    # Validate report structure
    assert "contact" in report
    assert "ats_summary" in report
    assert "top_matched_skills" in report
    assert "rewrite_highlights" in report
    assert "interview_preview" in report

    print("\n  POST /analyze [OK]")
    return result


def main():
    print("\n" + "#" * 60)
    print("  PHASE 5 TEST SUITE — FastAPI Endpoints")
    print("#" * 60)

    try:
        test_health()
    except Exception as e:
        print(f"\n  Health check failed: {e}")
        print("  Is the server running? Run: python run.py --port 8000")
        sys.exit(1)

    result = test_analyze()

    # Save output
    output_path = os.path.join(os.path.dirname(__file__), "phase5_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  Full output saved to: {output_path}")

    print("\n" + "#" * 60)
    print("  PHASE 5 COMPLETE [OK]")
    print("#" * 60)


if __name__ == "__main__":
    main()
