import React from "react"
import { motion } from "framer-motion"

export default function FactorBar({
  label,
  percent,
  value,
}: {
  label: string
  percent: number
  value: string
}) {
  return (
    <div>
      <div className="flex justify-between text-xs font-medium mb-1.5">
        <span className="text-foreground">{label}</span>
        <div className="flex gap-2 text-muted">
          <span className="text-[10px]">{value}</span>
          <span className="font-bold">{percent}%</span>
        </div>
      </div>
      <div className="h-1.5 w-full bg-muted-bg rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 1, delay: 0.2 }}
          className="h-full bg-risk-high rounded-full"
        />
      </div>
    </div>
  )
}
