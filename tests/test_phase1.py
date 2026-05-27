"""Phase 1 Test — Resume Parser Agent with DashScope Qwen.

Usage:
    python tests/test_phase1.py
    python tests/test_phase1.py --pdf path/to/resume.pdf
"""

import sys
import os
import argparse

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from backend.core.config import settings
from backend.core.logger import setup_logger

logger = setup_logger("test.phase1")


def test_config():
    """Test that configuration loads correctly from .env."""
    print("\n" + "=" * 60)
    print("TEST 1: Configuration Loading")
    print("=" * 60)
    settings.validate()
    print(f"  DASHSCOPE_API_KEY:  {'[OK] set' if settings.DASHSCOPE_API_KEY else '[MISSING]'}")
    print(f"  MODEL_NAME:         {settings.MODEL_NAME}")
    print(f"  MODEL_NAME_COMPLEX: {settings.MODEL_NAME_COMPLEX}")
    print(f"  DASHSCOPE_BASE_URL: {settings.DASHSCOPE_BASE_URL}")
    print("  Config [OK]")


def test_dashscope_connectivity():
    """Test that DashScope API is reachable and Qwen responds."""
    print("\n" + "=" * 60)
    print("TEST 2: DashScope Connectivity (qwen-plus)")
    print("=" * 60)

    import dashscope
    from dashscope import Generation

    dashscope.api_key = settings.DASHSCOPE_API_KEY

    response = Generation.call(
        model=settings.MODEL_NAME,
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        result_format="message",
    )

    if response.status_code == 200:
        content = response.output.choices[0].message.content
        print(f"  Response: {content.strip()}")
        print("  DashScope [OK]")
        return True
    else:
        print(f"  Error: code={response.code}, message={response.message}")
        print("  DashScope [FAILED]")
        return False


def test_pdf_extraction(pdf_path: str):
    """Test PDF text extraction."""
    print("\n" + "=" * 60)
    print("TEST 3: PDF Text Extraction")
    print("=" * 60)

    from backend.tools.pdf_parser import extract_text_from_pdf

    text = extract_text_from_pdf(pdf_path)
    print(f"  Characters extracted: {len(text)}")
    print(f"  First 200 chars: {text[:200]}...")
    print("  PDF extraction [OK]")
    return text


def test_resume_parser(resume_text: str):
    """Test the full resume parser agent."""
    print("\n" + "=" * 60)
    print("TEST 4: Resume Parser Agent")
    print("=" * 60)

    from backend.agents.resume_parser import parse_resume

    resume = parse_resume(resume_text)

    print(f"  Name:       {resume.contact.name if resume.contact else 'N/A'}")
    print(f"  Skills:     {len(resume.skills)} found → {resume.skills[:5]}...")
    print(f"  Experience: {len(resume.experience)} entries")
    for exp in resume.experience[:2]:
        print(f"    - {exp.title} at {exp.company}")
    print(f"  Projects:   {len(resume.projects)} found")
    for proj in resume.projects[:2]:
        print(f"    - {proj.name}")
    print(f"  Education:  {len(resume.education)} entries")

    # Validate the model
    print(f"\n  Resume model JSON:")
    print(f"  {resume.model_dump_json(indent=2)[:500]}...")
    print("\n  Resume Parser [OK]")
    return resume


def main():
    parser = argparse.ArgumentParser(description="Phase 1 Test Suite")
    parser.add_argument("--pdf", type=str, help="Path to a sample resume PDF")
    args = parser.parse_args()

    print("\n" + "█" * 60)
    print("  PHASE 1 TEST SUITE — Resume Parser Agent")
    print("█" * 60)

    test_config()

    if not test_dashscope_connectivity():
        print("\n❌ DashScope connectivity failed. Check your API key and network.")
        sys.exit(1)

    if args.pdf:
        resume_text = test_pdf_extraction(args.pdf)
        test_resume_parser(resume_text)
    else:
        print("\n" + "=" * 60)
        print("TEST 3-4: Skipped (no --pdf provided)")
        print("=" * 60)
        print("  Provide a sample resume PDF with: --pdf path/to/resume.pdf")

    print("\n" + "█" * 60)
    print("  PHASE 1 COMPLETE [OK]")
    print("█" * 60)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
