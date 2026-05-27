"use client";

interface ScoreGaugeProps {
  score: number;
  size?: "sm" | "lg";
}

function getScoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#eab308";
  return "#ef4444";
}

export function ScoreGauge({ score, size = "lg" }: ScoreGaugeProps) {
  const dim = size === "lg" ? 160 : 100;
  const strokeW = size === "lg" ? 10 : 8;
  const radius = (dim - strokeW) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = getScoreColor(score);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={dim} height={dim} className="drop-shadow-md">
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeW}
        />
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeW}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${dim / 2} ${dim / 2})`}
          className="transition-all duration-1000 ease-out"
        />
        <text
          x={dim / 2}
          y={dim / 2}
          textAnchor="middle"
          dominantBaseline="central"
          className={size === "lg" ? "text-3xl" : "text-xl"}
          fontWeight="bold"
          fill="#1e293b"
        >
          {score}
        </text>
      </svg>
      <span className="text-sm text-gray-500 font-medium">ATS 评分</span>
    </div>
  );
}
