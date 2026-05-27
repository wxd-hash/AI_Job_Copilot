"""SQLite 持久化存储。保存每次分析结果，支持历史查询和对比。"""

import sqlite3
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_lock = threading.Lock()

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent.parent.parent / "analyses.db")))


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """初始化数据库表。"""
    with _lock:
        conn = _get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                candidate_name TEXT DEFAULT '',
                job_title TEXT DEFAULT '',
                ats_score INTEGER DEFAULT 0,
                contact TEXT DEFAULT '{}',
                ats_summary TEXT DEFAULT '{}',
                top_skills TEXT DEFAULT '[]',
                missing_skills TEXT DEFAULT '[]',
                rewrite_highlights TEXT DEFAULT '[]',
                recommendations TEXT DEFAULT '[]',
                rewritten_resume TEXT DEFAULT '{}',
                interview_questions TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}',
                jd_text TEXT DEFAULT '',
                resume_snapshot TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyses_created
            ON analyses(created_at DESC)
        """)
        conn.commit()
        conn.close()


def save_analysis(
    session_id: str,
    report: dict,
    jd_text: str = "",
    resume_snapshot: dict | None = None,
) -> None:
    """保存一次完整分析结果。"""
    with _lock:
        conn = _get_conn()
        ats = report.get("ats_summary", {})
        conn.execute(
            """
            INSERT OR REPLACE INTO analyses (
                id, candidate_name, job_title, ats_score,
                contact, ats_summary, top_skills, missing_skills,
                rewrite_highlights, recommendations,
                rewritten_resume, interview_questions, metadata,
                jd_text, resume_snapshot, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                (report.get("contact") or {}).get("name", ""),
                ats.get("job_title", "") or "",
                ats.get("overall_score", 0) or 0,
                json.dumps(report.get("contact"), ensure_ascii=False),
                json.dumps(ats, ensure_ascii=False),
                json.dumps(report.get("top_matched_skills", []), ensure_ascii=False),
                json.dumps(report.get("critical_missing_skills", []), ensure_ascii=False),
                json.dumps(report.get("rewrite_highlights", []), ensure_ascii=False),
                json.dumps(report.get("recommendations", []), ensure_ascii=False),
                json.dumps(report.get("rewritten_resume") or {}, ensure_ascii=False),
                json.dumps(report.get("interview_questions") or {}, ensure_ascii=False),
                json.dumps(report.get("metadata", {}), ensure_ascii=False),
                jd_text[:5000] if jd_text else "",
                json.dumps(resume_snapshot or {}, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()


def list_analyses(limit: int = 20) -> list[dict]:
    """列出所有历史分析（简要信息）。"""
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            """
            SELECT id, candidate_name, job_title, ats_score, created_at
            FROM analyses ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        conn.close()
    return [
        {
            "id": r["id"],
            "candidate_name": r["candidate_name"],
            "job_title": r["job_title"],
            "ats_score": r["ats_score"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_analysis(analysis_id: str) -> dict | None:
    """获取单次分析完整结果。"""
    with _lock:
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
        ).fetchone()
        conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "candidate_name": row["candidate_name"],
        "job_title": row["job_title"],
        "ats_score": row["ats_score"],
        "contact": json.loads(row["contact"]),
        "ats_summary": json.loads(row["ats_summary"]),
        "top_matched_skills": json.loads(row["top_skills"]),
        "critical_missing_skills": json.loads(row["missing_skills"]),
        "rewrite_highlights": json.loads(row["rewrite_highlights"]),
        "recommendations": json.loads(row["recommendations"]),
        "rewritten_resume": json.loads(row["rewritten_resume"]),
        "interview_questions": json.loads(row["interview_questions"]),
        "metadata": json.loads(row["metadata"]),
        "jd_text": row["jd_text"],
        "resume_snapshot": json.loads(row["resume_snapshot"]),
        "created_at": row["created_at"],
    }


def delete_analysis(analysis_id: str) -> bool:
    """删除一次分析记录。"""
    with _lock:
        conn = _get_conn()
        cur = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        conn.commit()
        conn.close()
        return cur.rowcount > 0


# 启动时自动初始化
init_db()
