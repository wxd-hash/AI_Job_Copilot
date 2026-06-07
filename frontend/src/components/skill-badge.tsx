interface SkillBadgeProps {
  skill: string;
  variant: "matched" | "missing";
}

export function SkillBadge({ skill, variant }: SkillBadgeProps) {
  const base =
    "inline-flex items-center rounded-full px-3 py-1 text-sm font-medium transition-colors";
  const styles =
    variant === "matched"
      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
      : "bg-red-50 text-red-700 border border-red-200";

  return (
    <span className={`${base} ${styles}`}>
      {skill}
    </span>
  );
}
