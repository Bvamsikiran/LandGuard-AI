import React from "react"
import { RiskLevel } from "../../types"

export default function RiskBadge({ level, small = false }: { level: RiskLevel | string; small?: boolean }) {
  const colors: Record<string, string> = {
    Low: "bg-risk-low/10 text-risk-low border-risk-low/20",
    Moderate: "bg-risk-moderate/10 text-risk-moderate border-risk-moderate/30",
    High: "bg-risk-high/10 text-risk-high border-risk-high/30",
    "Very High": "bg-risk-very-high-bg text-risk-very-high border-risk-very-high/40 font-bold",
  }

  return (
    <span
      className={`${
        small ? "text-[10px] px-1.5 py-0.5" : "text-xs px-2.5 py-1"
      } rounded-md border uppercase tracking-wider ${colors[level] || colors.Low}`}
    >
      {level}
    </span>
  )
}
