import React from "react"

export default function StatCard({
  title,
  value,
  subtitle,
  risk,
  trend,
  trendType,
  isStatus,
}: {
  title: string
  value: string
  subtitle: string
  risk: string
  trend?: string
  trendType?: string
  isStatus?: boolean
}) {
  const riskBg: Record<string, string> = {
    low: "#10B981",
    moderate: "#F59E0B",
    high: "#F97316",
    "very high": "#EF4444",
  }

  const bg = riskBg[risk.toLowerCase()] ?? "#10B981"

  return (
    <div className="bg-card rounded-2xl border border-border shadow-sm p-5 flex flex-col relative overflow-hidden group hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
      <div
        className="absolute top-0 right-0 w-20 h-20 opacity-8 rounded-bl-full transition-transform duration-300 group-hover:scale-125 pointer-events-none"
        style={{ backgroundColor: bg, opacity: 0.08 }}
      ></div>
      <div className="text-xs font-medium text-muted mb-2 uppercase tracking-wider">{title}</div>
      <div className="text-3xl font-bold mb-2 text-foreground tracking-tight">
        {isStatus ? (
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-risk-low animate-pulse inline-block"></span>
            {value}
          </span>
        ) : (
          value
        )}
      </div>
      <div className="flex items-center justify-between mt-auto pt-2 border-t border-muted-bg">
        <div className="text-xs text-muted font-medium">{subtitle}</div>
        {trend && (
          <div
            className={`text-xs font-semibold ${
              trendType === "bad"
                ? "text-risk-high"
                : trendType === "good"
                ? "text-risk-low"
                : "text-muted"
            }`}
          >
            {trend}
          </div>
        )}
      </div>
    </div>
  )
}
