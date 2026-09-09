import React from "react"
import { motion } from "framer-motion"
import { AlertTriangle, CheckCircle2, X } from "lucide-react"
import { Alert } from "../../types"

export default function NotificationsPopover({
  alerts,
  onClose,
  onSelectAlert,
}: {
  alerts: Alert[]
  onClose: () => void
  onSelectAlert: (locationId: number) => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 10, scale: 0.95 }}
      className="absolute right-12 top-14 w-80 sm:w-96 bg-card border border-border rounded-2xl shadow-2xl z-50 overflow-hidden"
    >
      <div className="p-4 border-b border-border flex items-center justify-between bg-muted-bg/50">
        <div className="flex items-center gap-2">
          <h3 className="font-bold text-sm text-foreground">Notifications</h3>
          <span className="bg-risk-very-high text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
            {alerts.filter((a) => a.status === "Active").length} Active
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-muted hover:text-foreground p-1 rounded-lg hover:bg-card transition-colors"
        >
          <X size={15} />
        </button>
      </div>

      <div className="max-h-80 overflow-y-auto divide-y divide-border">
        {alerts.length === 0 ? (
          <div className="p-6 text-center text-xs text-muted">No notifications right now.</div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              onClick={() => {
                onSelectAlert(alert.locationId)
                onClose()
              }}
              className="p-3.5 hover:bg-muted-bg/60 cursor-pointer transition-colors flex items-start gap-3 group"
            >
              <div
                className={`size-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                  alert.level === "Very High"
                    ? "bg-risk-very-high/10 text-risk-very-high"
                    : alert.level === "High"
                    ? "bg-risk-high/10 text-risk-high"
                    : "bg-risk-moderate/10 text-risk-moderate"
                }`}
              >
                <AlertTriangle size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <div className="font-semibold text-xs text-foreground group-hover:text-primary transition-colors truncate">
                    {alert.location}
                  </div>
                  <span className="text-[10px] text-muted shrink-0 font-mono">{alert.time}</span>
                </div>
                <p className="text-[11px] text-muted line-clamp-2 leading-relaxed">
                  {alert.description || `${alert.level} landslide risk probability: ${alert.prob}`}
                </p>
                <div className="mt-1.5 flex items-center gap-2">
                  <span
                    className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                      alert.level === "Very High"
                        ? "bg-risk-very-high-bg text-risk-very-high"
                        : alert.level === "High"
                        ? "bg-risk-high-bg text-risk-high"
                        : "bg-risk-moderate/10 text-risk-moderate"
                    }`}
                  >
                    {alert.level} ({alert.prob})
                  </span>
                  {alert.status === "Acknowledged" && (
                    <span className="text-[9px] text-risk-low font-semibold flex items-center gap-0.5">
                      <CheckCircle2 size={10} /> Acknowledged
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="p-3 border-t border-border bg-muted-bg/30 text-center">
        <span className="text-[10px] text-muted font-medium">Northeast India Early Warning Stream</span>
      </div>
    </motion.div>
  )
}
