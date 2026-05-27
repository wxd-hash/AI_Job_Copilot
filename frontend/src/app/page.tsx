"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  Upload, Link, FileText, Loader2, ArrowLeft,
  ChevronDown, ChevronUp, AlertCircle, CheckCircle2, Circle,
  Clock, Share2, X, Trash2, Check,
} from "lucide-react";
import {
  submitAnalysis, getProgress, getResult,
  getHistory, getHistoryDetail, deleteHistoryItem,
  type HistoryItem,
} from "@/lib/api";

import type { Report, InterviewQuestion } from "@/lib/types";
import { ScoreGauge } from "@/components/score-gauge";
import { SkillBadge } from "@/components/skill-badge";
import { RewriteCard } from "@/components/rewrite-card";

type AppState = "form" | "loading" | "results";

const LOADING_STEPS = [
  { key: "resume_parsed", label: "解析简历结构" },
  { key: "jd_analyzed", label: "分析职位要求" },
  { key: "ats_scored", label: "计算 ATS 匹配评分" },
  { key: "rewrite_done", label: "生成简历优化建议" },
  { key: "interview_done", label: "编写面试题目" },
];

const DIFFICULTY_MAP: Record<string, string> = {
  hard: "困难",
  medium: "中等",
  easy: "简单",
};

const BREAKDOWN_LABELS: Record<string, string> = {
  Technical: "技术匹配",
  Experience: "经验匹配",
  Education: "学历匹配",
  Keywords: "关键词",
};

const INTERVIEW_TABS = [
  { key: "technical", label: "技术面试", icon: "💻" },
  { key: "behavioral", label: "行为面试", icon: "🤝" },
  { key: "situational", label: "情景面试", icon: "🎯" },
  { key: "gap", label: "缺口探测", icon: "🔍" },
] as const;

function QuestionCard({ q }: { q: InterviewQuestion }) {
  return (
    <div className="bg-white border rounded-xl p-4 shadow-sm space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            q.difficulty === "hard"
              ? "bg-red-50 text-red-600"
              : q.difficulty === "medium"
                ? "bg-amber-50 text-amber-600"
                : "bg-emerald-50 text-emerald-600"
          }`}
        >
          {DIFFICULTY_MAP[q.difficulty] ?? q.difficulty}
        </span>
        <span className="text-xs text-gray-400">{q.focus_area}</span>
      </div>
      <p className="text-sm text-gray-800 font-medium">{q.question}</p>
      {q.expected_topics.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {q.expected_topics.map((t) => (
            <span
              key={t}
              className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-0.5"
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [state, setState] = useState<AppState>("form");
  const [file, setFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState("");
  const [jdUrl, setJdUrl] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [rewriteExpanded, setRewriteExpanded] = useState(false);
  const [interviewTab, setInterviewTab] = useState<string>("technical");
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [gapExpanded, setGapExpanded] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);

  // 历史记录
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [shared, setShared] = useState(false);

  const canSubmit = file && (jdText.trim() || jdUrl.trim());
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 分享链接加载
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const shareId = params.get("share");
    if (shareId) {
      setState("loading");
      setCompletedSteps(LOADING_STEPS.map((s) => s.key));
      getHistoryDetail(shareId).then((res) => {
        if (res.report) {
          setReport(res.report);
          setState("results");
          window.history.replaceState({}, "", "/");
        } else {
          setState("form");
        }
      }).catch(() => {
        setState("form");
      });
    }
  }, []);

  // 加载历史
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const items = await getHistory();
      setHistory(items);
    } catch { /* ignore */ }
    setHistoryLoading(false);
  }, []);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;
    setState("loading");
    setError("");
    setCompletedSteps([]);

    try {
      const sessionId = await submitAnalysis(file!, jdText, jdUrl);

      pollingRef.current = setInterval(async () => {
        try {
          const progress = await getProgress(sessionId);
          setCompletedSteps([...progress.completed]);

          if (progress.completed.length >= progress.total_steps) {
            if (pollingRef.current) clearInterval(pollingRef.current);

            try {
              const res = await getResult(sessionId);
              if (!res.report) {
                throw new Error("分析未返回有效报告");
              }
              setReport(res.report);
              setState("results");
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : "未知错误";
              setError(msg);
              setState("form");
            }
          }
        } catch {
          // 轮询失败静默跳过，下次继续
        }
      }, 1500);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "未知错误";
      setError(msg);
      setState("form");
    }
  }, [canSubmit, file, jdText, jdUrl]);

  const reset = () => {
    setState("form");
    setReport(null);
    setError("");
    setRewriteExpanded(false);
    setSummaryExpanded(false);
    setGapExpanded(false);
    setInterviewTab("technical");
  };

  // ── 表单 ─────────────────────────────────────────────────────────
  if (state === "form") {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-2xl space-y-8">
          <header className="text-center space-y-2">
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              AI 求职助手
            </h1>
            <p className="text-gray-500">
              上传简历 PDF，输入职位描述，即可获得 ATS 评分、简历优化建议和面试题
            </p>
          </header>

          <div
            className={`relative border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${
              dragOver
                ? "border-primary-400 bg-primary-50"
                : file
                  ? "border-emerald-300 bg-emerald-50/50"
                  : "border-gray-300 hover:border-gray-400 bg-white"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault(); setDragOver(false);
              const f = e.dataTransfer.files[0];
              if (f?.type === "application/pdf") setFile(f);
            }}
            onClick={() => document.getElementById("pdf-input")?.click()}
          >
            <input
              id="pdf-input" type="file" accept="application/pdf"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }}
            />
            {file ? (
              <div className="space-y-1">
                <FileText className="w-10 h-10 text-emerald-500 mx-auto" />
                <p className="font-medium text-emerald-700">{file.name}</p>
                <p className="text-sm text-emerald-600">
                  {(file.size / 1024).toFixed(0)} KB — 点击更换
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload className="w-10 h-10 text-gray-400 mx-auto" />
                <p className="font-medium text-gray-700">拖拽简历 PDF 到此处</p>
                <p className="text-sm text-gray-400">或点击选择文件（仅 PDF，最大 10MB）</p>
              </div>
            )}
          </div>

          <div className="space-y-3">
            <textarea
              rows={6}
              placeholder="在此粘贴职位描述（JD）..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent placeholder:text-gray-400 resize-none bg-white"
            />
            <div className="flex items-center gap-2 text-gray-400">
              <span className="h-px flex-1 bg-gray-200" />
              <span className="text-xs font-medium">或者</span>
              <span className="h-px flex-1 bg-gray-200" />
            </div>
            <div className="relative">
              <Link className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="url" placeholder="职位链接（选填）"
                value={jdUrl}
                onChange={(e) => setJdUrl(e.target.value)}
                className="w-full rounded-xl border border-gray-300 pl-10 pr-4 py-3 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent placeholder:text-gray-400 bg-white"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 px-5 py-4 space-y-2">
              <span className="text-red-500 font-semibold text-sm">出错了</span>
              <p className="text-sm text-red-700 whitespace-pre-wrap leading-relaxed">{error}</p>
            </div>
          )}

          <button
            onClick={handleSubmit} disabled={!canSubmit}
            className={`w-full rounded-xl py-3.5 font-semibold text-white transition-all ${
              canSubmit
                ? "bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-200 active:scale-[0.98]"
                : "bg-gray-300 cursor-not-allowed"
            }`}
          >
            开始分析
          </button>

          {/* 历史记录按钮 */}
          <button
            onClick={() => { setHistoryOpen(true); loadHistory(); }}
            className="w-full flex items-center justify-center gap-2 py-2.5 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-xl transition-colors"
          >
            <Clock className="w-4 h-4" />
            历史记录
          </button>
        </div>

        {/* ── 历史记录抽屉 ── */}
        {historyOpen && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <div className="absolute inset-0 bg-black/30" onClick={() => setHistoryOpen(false)} />
            <div className="relative w-full max-w-md bg-white h-full overflow-y-auto shadow-2xl animate-slide-up">
              <div className="sticky top-0 bg-white border-b px-5 py-4 flex items-center justify-between z-10">
                <h2 className="text-lg font-semibold text-gray-900">历史记录</h2>
                <button onClick={() => setHistoryOpen(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              {historyLoading ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : history.length === 0 ? (
                <p className="text-center text-gray-400 py-12 text-sm">暂无分析记录</p>
              ) : (
                <div className="divide-y">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      onClick={async () => {
                        try {
                          const res = await getHistoryDetail(item.id);
                          if (res.report) {
                            setReport(res.report);
                            setState("results");
                            setHistoryOpen(false);
                          }
                        } catch { /* ignore */ }
                      }}
                      className="px-5 py-4 hover:bg-gray-50 cursor-pointer group"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-gray-900 text-sm truncate">
                            {item.candidate_name || "未命名"}
                          </p>
                          <p className="text-xs text-gray-500 truncate mt-0.5">
                            {item.job_title || "未知职位"}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {item.created_at?.slice(0, 16).replace("T", " ")}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-sm font-bold ${
                            item.ats_score >= 80 ? "text-emerald-600" :
                            item.ats_score >= 60 ? "text-amber-600" : "text-red-600"
                          }`}>
                            {item.ats_score}
                          </span>
                          <span className="text-xs text-gray-400">分</span>
                          <button
                            onClick={async (e) => {
                              e.stopPropagation();
                              if (!window.confirm("确定要删除这条记录吗？此操作不可撤销。")) return;
                              await deleteHistoryItem(item.id);
                              setHistory(history.filter((h) => h.id !== item.id));
                            }}
                            className="hidden group-hover:flex p-1.5 hover:bg-red-50 rounded-lg"
                            title="删除"
                          >
                            <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}

                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── 加载 ─────────────────────────────────────────────────────────
  if (state === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-6 animate-fade-in">
          <div className="text-center space-y-2">
            <Loader2 className="w-10 h-10 text-primary-500 animate-spin mx-auto" />
            <p className="text-lg font-medium text-gray-700">正在分析你的简历...</p>
            <p className="text-sm text-gray-400">
              {completedSteps.length === 0
                ? "准备中..."
                : `已完成 ${completedSteps.length} / ${LOADING_STEPS.length} 步`}
            </p>
          </div>

          <div className="space-y-2">
            {LOADING_STEPS.map((step, i) => {
              const done = completedSteps.includes(step.key);
              const current = !done && (i === completedSteps.length);
              return (
                <div
                  key={step.key}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ${
                    done
                      ? "bg-emerald-50 border border-emerald-200"
                      : current
                        ? "bg-primary-50 border border-primary-200"
                        : "bg-gray-50 border border-gray-100"
                  }`}
                >
                  {done ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                  ) : current ? (
                    <Loader2 className="w-5 h-5 text-primary-500 animate-spin shrink-0" />
                  ) : (
                    <Circle className="w-5 h-5 text-gray-300 shrink-0" />
                  )}
                  <span
                    className={`text-sm font-medium ${
                      done
                        ? "text-emerald-700"
                        : current
                          ? "text-primary-700"
                          : "text-gray-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // ── 结果 ─────────────────────────────────────────────────────────
  if (!report) return null;

  const { ats_summary: ats } = report;
  const fullRewrite = report.rewritten_resume;
  const fullInterview = report.interview_questions;

  // 获取当前 tab 的面试题
  const getQuestionsForTab = (tab: string): InterviewQuestion[] => {
    if (!fullInterview) return [];
    switch (tab) {
      case "technical": return fullInterview.technical_questions ?? [];
      case "behavioral": return fullInterview.behavioral_questions ?? [];
      case "situational": return fullInterview.situational_questions ?? [];
      case "gap": return fullInterview.gap_probing_questions ?? [];
      default: return [];
    }
  };

  const visibleBullets = rewriteExpanded
    ? report.rewrite_highlights
    : report.rewrite_highlights.slice(0, 2);

  return (
    <div className="min-h-screen py-8 px-4 animate-fade-in">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <button
            onClick={reset}
            className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            重新分析
          </button>
          {/* 分享链接 */}
          {report.session_id && (
            <button
              onClick={() => {
                const url = `${window.location.origin}/?share=${report.session_id}`;
                navigator.clipboard.writeText(url).then(() => {
                  setShared(true);
                  setTimeout(() => setShared(false), 2000);
                });
              }}
              className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-primary-600 transition-colors"
            >
              {shared ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                  已复制
                </>
              ) : (
                <>
                  <Share2 className="w-3.5 h-3.5" />
                  分享链接
                </>
              )}
            </button>
          )}
        </div>

        {/* ── 评分总览 ── */}
        <div className="bg-white rounded-2xl border p-8 shadow-sm">
          <div className="flex flex-col sm:flex-row items-center gap-8">
            <ScoreGauge score={ats.overall_score} />
            <div className="space-y-3 text-center sm:text-left">
              <h2 className="text-2xl font-bold text-gray-900">
                {report.contact?.name ?? "候选人"}
              </h2>
              <p className="text-gray-500 text-sm leading-relaxed max-w-md">{ats.reasoning}</p>
              <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
                {report.top_matched_skills.map((s) => (
                  <SkillBadge key={s} skill={s} variant="matched" />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── 四维评分 ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            ["Technical", ats.technical_match],
            ["Experience", ats.experience_match],
            ["Education", ats.education_match],
            ["Keywords", ats.keyword_match],
          ].map(([key, value]) => (
            <div key={key} className="bg-white rounded-xl border p-4 text-center shadow-sm">
              <div className="text-2xl font-bold text-gray-900">{value}%</div>
              <div className="text-xs text-gray-500 mt-1">{BREAKDOWN_LABELS[key] ?? key}</div>
              <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 rounded-full transition-all duration-700"
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* ── 简历优化建议 ── */}
        {report.rewrite_highlights.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                简历优化建议
                <span className="ml-2 text-sm font-normal text-gray-400">
                  {report.rewrite_highlights.length} 条
                </span>
              </h3>
              {fullRewrite?.suggested_summary && (
                <button
                  onClick={() => setSummaryExpanded(!summaryExpanded)}
                  className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                >
                  {summaryExpanded ? "收起优化简介" : "查看优化简介"}
                </button>
              )}
            </div>

            {/* 优化后的个人简介 */}
            {summaryExpanded && fullRewrite?.suggested_summary && (
              <div className="bg-primary-50 border border-primary-200 rounded-xl p-4 text-sm text-primary-800 leading-relaxed animate-slide-up">
                <span className="text-xs font-semibold text-primary-500 uppercase tracking-wider">
                  优化后个人简介
                </span>
                <p className="mt-2">{fullRewrite.suggested_summary}</p>
              </div>
            )}

            {/* Bullet 改写 */}
            <div className="grid gap-3">
              {visibleBullets.map((r, i) => (
                <div
                  key={i}
                  className="animate-slide-up"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <RewriteCard
                    section={r.section}
                    original={r.original}
                    rewritten={r.rewritten}
                    addedKeywords={r.added_keywords}
                  />
                </div>
              ))}
            </div>

            {report.rewrite_highlights.length > 2 && (
              <button
                onClick={() => setRewriteExpanded(!rewriteExpanded)}
                className="w-full flex items-center justify-center gap-1.5 py-2.5 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-xl transition-colors"
              >
                {rewriteExpanded ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    收起（仅显示前 2 条）
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    展开全部 {report.rewrite_highlights.length} 条优化建议
                  </>
                )}
              </button>
            )}

            {/* 技能缺口计划 */}
            {fullRewrite && fullRewrite.skill_gap_plan.length > 0 && (
              <div>
                <button
                  onClick={() => setGapExpanded(!gapExpanded)}
                  className="flex items-center gap-2 text-sm text-amber-600 font-medium hover:text-amber-700"
                >
                  <AlertCircle className="w-4 h-4" />
                  技能缺口补救计划（{fullRewrite.skill_gap_plan.length} 项）
                  {gapExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
                {gapExpanded && (
                  <div className="mt-3 space-y-2 animate-slide-up">
                    {fullRewrite.skill_gap_plan.map((gap, i) => (
                      <div
                        key={i}
                        className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-3"
                      >
                        <span
                          className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full mt-0.5 ${
                            gap.priority === "high"
                              ? "bg-red-100 text-red-700"
                              : gap.priority === "medium"
                                ? "bg-amber-100 text-amber-700"
                                : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {gap.priority === "high" ? "高优先" : gap.priority === "medium" ? "中优先" : "低优先"}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-amber-800">{gap.missing_skill}</p>
                          <p className="text-xs text-amber-600 mt-0.5">{gap.suggestion}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* ── 面试题 ── */}
        {fullInterview && (
          <section className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">
              面试题
              <span className="ml-2 text-sm font-normal text-gray-400">
                {(() => {
                  const t = fullInterview;
                  return (
                    (t.technical_questions?.length ?? 0) +
                    (t.behavioral_questions?.length ?? 0) +
                    (t.situational_questions?.length ?? 0) +
                    (t.gap_probing_questions?.length ?? 0)
                  );
                })()} 题
              </span>
            </h3>

            {/* Tab 切换 */}
            <div className="flex gap-1 bg-gray-100 rounded-xl p-1 overflow-x-auto">
              {INTERVIEW_TABS.map((tab) => {
                const count = getQuestionsForTab(tab.key).length;
                if (count === 0) return null;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setInterviewTab(tab.key)}
                    className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                      interviewTab === tab.key
                        ? "bg-white text-gray-900 shadow-sm"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    <span>{tab.icon}</span>
                    {tab.label}
                    <span className="text-xs text-gray-400 ml-0.5">{count}</span>
                    {tab.key === "gap" && (
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* 追问策略（仅缺口 tab 显示） */}
            {interviewTab === "gap" && fullInterview.follow_up_strategy && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800 animate-slide-up">
                <span className="text-xs font-semibold text-blue-500">追问策略</span>
                <p className="mt-1">{fullInterview.follow_up_strategy}</p>
              </div>
            )}

            {/* 题目列表 */}
            <div className="space-y-2">
              {getQuestionsForTab(interviewTab).map((q, i) => (
                <div
                  key={i}
                  className="animate-slide-up"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <QuestionCard q={q} />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── 改进建议 ── */}
        {report.recommendations.length > 0 && (
          <section className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">
              改进建议
              <span className="ml-2 text-sm font-normal text-gray-400">
                {report.recommendations.length} 条
              </span>
            </h3>
            <div className="bg-white border rounded-xl divide-y shadow-sm">
              {report.recommendations.map((r, i) => (
                <div key={i} className="flex items-start gap-3 px-5 py-4">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <p className="text-sm text-gray-700">{r}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        <footer className="text-center text-xs text-gray-400 pb-8">
          AI 求职助手 — 由 Qwen (DashScope) + LangGraph 驱动
        </footer>
      </div>
    </div>
  );
}
