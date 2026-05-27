const SECTION_LABELS: Record<string, string> = {
  experience: "工作经历",
  skills: "技能",
  summary: "个人简介",
  projects: "项目经历",
  "工作经历": "工作经历",
  "技能": "技能",
  "个人简介": "个人简介",
  "项目经历": "项目经历",
};

interface RewriteCardProps {
  section: string;
  original: string;
  rewritten: string;
  addedKeywords?: string[];
}

export function RewriteCard({ section, original, rewritten, addedKeywords }: RewriteCardProps) {
  const label = SECTION_LABELS[section] ?? section;
  return (
    <div className="bg-white border rounded-xl p-5 space-y-3 shadow-sm
                    hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-primary-600 bg-primary-50 px-2.5 py-1 rounded-full">
          {label}
        </span>
        {addedKeywords && addedKeywords.length > 0 && (
          <div className="flex gap-1 flex-wrap justify-end">
            {addedKeywords.map((kw) => (
              <span key={kw} className="text-xs text-emerald-600 bg-emerald-50 rounded-full px-2 py-0.5">
                +{kw}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-start gap-2">
          <span className="text-xs font-medium text-gray-400 bg-gray-100 rounded px-1.5 py-0.5 mt-0.5 shrink-0">
            修改前
          </span>
          <p className="text-sm text-gray-600 leading-relaxed">{original}</p>
        </div>
        <div className="flex items-start gap-2">
          <span className="text-xs font-medium text-emerald-600 bg-emerald-50 rounded px-1.5 py-0.5 mt-0.5 shrink-0">
            修改后
          </span>
          <p className="text-sm text-gray-900 leading-relaxed font-medium">
            {rewritten}
          </p>
        </div>
      </div>
    </div>
  );
}
