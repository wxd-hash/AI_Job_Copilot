"""进度追踪模块。管道节点通过 session_id 写入当前阶段，前端轮询读取。"""

import threading
from datetime import datetime, timezone

_lock = threading.Lock()
_store: dict[str, dict] = {}

STEPS = [
    "resume_parsed",    # 解析简历结构
    "jd_analyzed",      # 分析职位要求
    "ats_scored",       # 计算 ATS 匹配评分
    "rewrite_done",     # 生成简历优化建议
    "interview_done",   # 编写面试题目
]

STEP_LABELS: dict[str, str] = {
    "resume_parsed": "解析简历结构",
    "jd_analyzed": "分析职位要求",
    "ats_scored": "计算 ATS 匹配评分",
    "rewrite_done": "生成简历优化建议",
    "interview_done": "编写面试题目",
}


def create_session() -> str:
    """创建新会话，返回 session_id。"""
    import uuid
    sid = uuid.uuid4().hex[:12]
    with _lock:
        _store[sid] = {
            "completed": [],
            "current": "initialized",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    return sid


def update_progress(session_id: str, stage: str) -> None:
    """记录管道节点的完成状态。"""
    with _lock:
        if session_id in _store:
            if stage not in _store[session_id]["completed"]:
                _store[session_id]["completed"].append(stage)
            _store[session_id]["current"] = stage


def get_progress(session_id: str) -> dict | None:
    """获取会话进度。"""
    with _lock:
        return _store.get(session_id)


def set_result(session_id: str, result: dict) -> None:
    """存储管道的最终结果。"""
    with _lock:
        if session_id in _store:
            _store[session_id]["result"] = result


def get_result(session_id: str) -> dict | None:
    """获取管道最终结果。"""
    with _lock:
        session = _store.get(session_id)
        return session.get("result") if session else None


def cleanup_session(session_id: str) -> None:
    """清理已完成会话。"""
    with _lock:
        _store.pop(session_id, None)
