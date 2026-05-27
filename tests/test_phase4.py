"""Phase 4 Test — Full LangGraph Pipeline E2E.

Usage:
    python tests/test_phase4.py                # auto-generates test PDF
    python tests/test_phase4.py --pdf resume.pdf
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
logger = setup_logger("test.phase4")

# ── Sample JD text (same as Phase 2) ──────────────────────────────────

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


def create_test_pdf(output_path: str) -> str:
    """Create a test resume PDF using PyMuPDF."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()

    resume_text = (
        "ZHANG WEI\n"
        "Senior Backend Engineer\n"
        "zhangwei@example.com | +86 138-0000-1234 | Beijing, China\n"
        "linkedin.com/in/zhangwei | github.com/zhangwei\n\n"
        "PROFESSIONAL SUMMARY\n"
        "Senior Python backend engineer with 5 years of experience building "
        "distributed systems and data pipelines. Strong in FastAPI, PostgreSQL, "
        "Docker, and AWS.\n\n"
        "SKILLS\n"
        "Python, FastAPI, Django, PostgreSQL, MySQL, Redis, Docker, Kubernetes, "
        "AWS, Git, CI/CD, REST API, Microservices, SQLAlchemy, Pytest, Linux, Agile\n\n"
        "WORK EXPERIENCE\n\n"
        "Senior Backend Engineer | TechCorp Beijing | 2022-03 to Present\n"
        "- Designed and built 12 microservices handling 50k req/s\n"
        "- Led migration from monolith to Kubernetes-based architecture\n"
        "- Reduced API latency by 40% through query optimization\n\n"
        "Backend Developer | StartupXYZ | 2019-07 to 2022-02\n"
        "- Built REST APIs with FastAPI and PostgreSQL\n"
        "- Implemented CI/CD pipelines with GitHub Actions\n"
        "- Developed internal data pipeline processing 2TB daily\n\n"
        "PROJECTS\n"
        "Real-time Analytics Platform\n"
        "Streaming analytics system using Kafka and Flink\n"
        "Technologies: Python, Kafka, Flink, PostgreSQL, Docker\n\n"
        "EDUCATION\n"
        "B.S. Computer Science | Tsinghua University | 2019\n\n"
        "CERTIFICATIONS\n"
        "AWS Solutions Architect Associate\n\n"
        "LANGUAGES\n"
        "Chinese (Native), English (Fluent)"
    )

    # Insert text at a reasonable position
    rect = fitz.Rect(50, 50, 545, 792)
    page.insert_textbox(rect, resume_text, fontsize=10, fontname="helv")

    doc.save(output_path)
    doc.close()
    logger.info("Created test PDF: %s", output_path)
    return output_path


def test_full_pipeline(pdf_path: str, jd_text: str):
    """Run the complete LangGraph pipeline."""
    print("\n" + "#" * 60)
    print("  PHASE 4: FULL LANGGRAPH PIPELINE")
    print("#" * 60)

    from backend.workflows.graph import run_pipeline

    print(f"\n  Input:")
    print(f"    PDF: {pdf_path}")
    print(f"    JD:  {len(jd_text)} chars")

    print("\n  Running pipeline...\n")

    final_state = run_pipeline(pdf_path=pdf_path, jd_text=jd_text)

    # ── Check for errors ──
    error = final_state.get("error", "")
    if error:
        print(f"\n  PIPELINE ERROR: {error}")
        return None

    current_stage = final_state.get("current_stage", "unknown")
    print(f"\n  Pipeline completed: stage={current_stage}")

    # ── Print results ──

    resume = final_state.get("resume", {})
    contact = resume.get("contact", {})
    print(f"\n  [Resume] {contact.get('name', 'N/A')} — "
          f"{len(resume.get('skills', []))} skills, "
          f"{len(resume.get('experience', []))} experiences")

    jd = final_state.get("jd", {})
    print(f"  [JD] {jd.get('role_title', 'N/A')} — "
          f"{jd.get('seniority_level', 'N/A')}, "
          f"{len(jd.get('required_skills', []))} required skills")

    ats = final_state.get("ats", {})
    print(f"  [ATS] Score: {ats.get('overall_score', '?')}/100 — "
          f"{len(ats.get('matched_skills', []))} matched, "
          f"{len(ats.get('missing_skills', []))} missing")

    rewritten = final_state.get("rewritten_resume", {})
    print(f"  [Rewrite] {len(rewritten.get('improved_bullets', []))} improved bullets, "
          f"{len(rewritten.get('skill_gap_plan', []))} gap actions")

    interview = final_state.get("interview_questions", {})
    total_q = (
        len(interview.get("behavioral_questions", []))
        + len(interview.get("technical_questions", []))
        + len(interview.get("situational_questions", []))
        + len(interview.get("gap_probing_questions", []))
    )
    print(f"  [Interview] {total_q} total questions generated")

    report = final_state.get("final_report", {})
    metadata = report.get("metadata", {})
    print(f"\n  [Report] Generated with timings:")
    for key in ["resume_parser_duration_s", "jd_analyzer_duration_s",
                 "ats_scorer_duration_s", "rewrite_agent_duration_s",
                 "interview_agent_duration_s"]:
        val = metadata.get(key)
        if val:
            print(f"    {key}: {val:.2f}s")

    # ── Validation ──
    assert not error, f"Pipeline had error: {error}"
    assert resume, "Missing resume output"
    assert jd, "Missing JD output"
    assert ats, "Missing ATS output"
    assert rewritten, "Missing rewrite output"
    assert interview, "Missing interview output"
    assert report, "Missing final report"
    assert 0 <= ats.get("overall_score", -1) <= 100, "Invalid ATS score"

    print(f"\n  Full Pipeline [OK]")
    return final_state


def test_graph_structure():
    """Print the compiled graph structure for verification."""
    print("\n" + "=" * 60)
    print("TEST 0: Graph Structure")
    print("=" * 60)

    from backend.workflows.graph import get_pipeline
    graph = get_pipeline()
    # Print nodes and edges from compiled graph
    nodes = graph.get_graph().nodes
    edges = graph.get_graph().edges

    print(f"  Nodes: {list(nodes.keys())}")
    print(f"  Edges: {[str(e) for e in edges]}")
    print("  Graph Structure [OK]")


def main():
    parser = __import__("argparse").ArgumentParser(description="Phase 4 Test Suite")
    parser.add_argument("--pdf", type=str, help="Path to a resume PDF")
    parser.add_argument("--jd", type=str, help="JD text or use built-in sample")
    args = parser.parse_args()

    test_graph_structure()

    # Get or create PDF
    if args.pdf:
        pdf_path = args.pdf
    else:
        print("\n  No --pdf provided, generating test resume PDF...")
        tmp_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(tmp_dir, "test_resume.pdf")
        create_test_pdf(pdf_path)

    jd_text = args.jd if args.jd else SAMPLE_JD_TEXT

    result = test_full_pipeline(pdf_path, jd_text)

    if result:
        output_path = os.path.join(
            os.path.dirname(__file__), "phase4_output.json"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            # Serialize only the final report for readability
            json.dump(result.get("final_report", {}), f, ensure_ascii=False, indent=2)
        print(f"\n  Report saved to: {output_path}")

    print("\n" + "#" * 60)
    print("  PHASE 4 COMPLETE [OK]")
    print("#" * 60)


if __name__ == "__main__":
    main()
