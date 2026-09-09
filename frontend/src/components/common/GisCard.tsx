import React from "react"

export default function GisCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-muted-bg p-3 rounded-xl border border-border">
      <div className="text-[10px] uppercase font-bold text-muted tracking-wider mb-1">{label}</div>
      <div className="text-sm font-semibold text-foreground font-mono truncate">{value}</div>
    </div>
  )
}
