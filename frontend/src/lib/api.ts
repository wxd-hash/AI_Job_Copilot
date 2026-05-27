import type { AnalyzeResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SubmitResponse {
  status: string;
  session_id: string;
}

interface ProgressResponse {
  session_id: string;
  completed: string[];
  current: string;
  total_steps: number;
  step_labels: Record<string, string>;
}

export async function submitAnalysis(
  file: File,
  jdText: string,
  jdUrl: string
): Promise<string> {
  const formData = new FormData();
  formData.append("resume_pdf", file);
  if (jdText.trim()) formData.append("jd_text", jdText.trim());
  if (jdUrl.trim()) formData.append("jd_url", jdUrl.trim());

  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = err.detail || `请求失败 (HTTP ${res.status})`;
    throw new Error(msg);
  }

  const data: SubmitResponse = await res.json();
  return data.session_id;
}

export async function getProgress(sessionId: string): Promise<ProgressResponse> {
  const res = await fetch(`${API_BASE}/progress/${sessionId}`);
  if (!res.ok) throw new Error("获取进度失败");
  return res.json();
}

export async function getResult(sessionId: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/result/${sessionId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `获取结果失败 (HTTP ${res.status})`);
  }

  const data = await res.json();

  if (data.status === "processing") {
    throw new Error("分析尚未完成");
  }

  if (data.status === "error") {
    throw new Error(data.error || "分析失败");
  }

  return data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    return data.status === "healthy";
  } catch {
    return false;
  }
}

export interface HistoryItem {
  id: string;
  candidate_name: string;
  job_title: string;
  ats_score: number;
  created_at: string;
}

export async function getHistory(): Promise<HistoryItem[]> {
  const res = await fetch(`${API_BASE}/history`);
  if (!res.ok) throw new Error("获取历史记录失败");
  const data = await res.json();
  return data.analyses;
}

export async function getHistoryDetail(id: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/history/${id}`);
  if (!res.ok) throw new Error("记录不存在");
  const data = await res.json();
  return { status: "completed", report: data };
}

export async function deleteHistoryItem(id: string): Promise<void> {
  await fetch(`${API_BASE}/history/${id}`, { method: "DELETE" });
}
