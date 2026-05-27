export interface Contact {
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
}

export interface ATSSummary {
  overall_score: number;
  technical_match: number;
  experience_match: number;
  education_match: number;
  keyword_match: number;
  reasoning: string;
}

export interface RewriteBullet {
  section: string;
  original: string;
  rewritten: string;
  added_keywords: string[];
}

export interface InterviewQuestion {
  question: string;
  category: string;
  difficulty: string;
  focus_area: string;
  expected_topics: string[];
}

export interface RewrittenResume {
  improved_bullets: RewriteBullet[];
  suggested_summary: string;
  skill_gap_plan: {
    missing_skill: string;
    suggestion: string;
    priority: string;
  }[];
  keyword_additions: string[];
}

export interface InterviewQuestions {
  behavioral_questions: InterviewQuestion[];
  technical_questions: InterviewQuestion[];
  situational_questions: InterviewQuestion[];
  gap_probing_questions: InterviewQuestion[];
  follow_up_strategy: string;
}

export interface Report {
  metadata: {
    started_at: string;
    completed_at?: string;
    resume_parser_duration_s?: number;
    jd_analyzer_duration_s?: number;
    ats_scorer_duration_s?: number;
    rewrite_agent_duration_s?: number;
    interview_agent_duration_s?: number;
  };
  contact?: Contact;
  ats_summary: ATSSummary;
  top_matched_skills: string[];
  critical_missing_skills: string[];
  rewrite_highlights: RewriteBullet[];
  interview_preview: InterviewQuestion[];
  recommendations: string[];
  rewritten_resume?: RewrittenResume;
  interview_questions?: InterviewQuestions;
  session_id?: string;
}

export interface AnalyzeResponse {
  status: "completed" | "error";
  report?: Report;
  error?: string;
  stage?: string;
  partial_report?: Report | null;
}
