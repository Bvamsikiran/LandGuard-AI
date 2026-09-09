import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { AlertTriangle, Filter, Eye, CheckCircle2, AlertCircle, MessageSquare, X } from "lucide-react"
import { Alert } from "../types"
import RiskBadge from "../components/common/RiskBadge"

const API_BASE = "/api/v1"

async function dispatchSMSAlert(alert: Alert): Promise<{ demo_mode: boolean; message_preview: string; recipients_count: number; integration_note: string }> {
  const res = await fetch(`${API_BASE}/risk/alerts/sms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      alert_id: alert.id,
      location: alert.location,
      risk_level: alert.level,
      probability: alert.prob,
      state: alert.state,
      provider: "twilio",
    }),
  })
  if (!res.ok) throw new Error(`SMS API error ${res.status}`)
  return res.json()
}

export default function AlertsView({
  alerts,
  selectedRegion,
  onViewDetails,
  onAcknowledge,
}: {
  alerts: Alert[]
  selectedRegion: string
  onViewDetails: (locationId: number) => void
  onAcknowledge: (alertId: number) => void
}) {
  const [showFilter, setShowFilter] = useState(false)
  const [filterSeverity, setFilterSeverity] = useState<string[]>(["Very High", "High", "Moderate"])
  const [filterStatus, setFilterStatus] = useState<string[]>(["Active", "Acknowledged"])
  const [smsLoading, setSmsLoading] = useState<number | null>(null)
  const [smsResult, setSmsResult] = useState<{ alert: Alert; data: Awaited<ReturnType<typeof dispatchSMSAlert>> } | null>(null)

  const regionAlerts =
    selectedRegion === "Northeastern India"
      ? alerts
      : alerts.filter((a) => a.state.toLowerCase() === selectedRegion.toLowerCase())

  const filteredAlerts = regionAlerts.filter(
    (a) => filterSeverity.includes(a.level) && filterStatus.includes(a.status)
  )

  const veryHighCount = regionAlerts.filter((a) => a.level === "Very High" && a.status === "Active").length
  const highCount = regionAlerts.filter((a) => a.level === "High" && a.status === "Active").length
  const moderateCount = regionAlerts.filter((a) => a.level === "Moderate" && a.status === "Active").length
  const totalActive = regionAlerts.filter((a) => a.status === "Active").length

  return (
    <div className="p-6 sm:p-8 max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Active Risk Alerts</h1>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            {selectedRegion} · Real-time AI Hazard Broadcasts
          </p>
        </div>
        <div className="relative self-start sm:self-auto">
          <button
            onClick={() => setShowFilter(!showFilter)}
            className={`px-4 py-2.5 text-xs font-bold border rounded-xl flex items-center gap-2 transition-colors ${
              showFilter
                ? "bg-muted-bg border-border text-foreground"
                : "border-border bg-card hover:bg-muted-bg text-foreground shadow-xs"
            }`}
          >
            <Filter size={15} /> Filter Alerts
          </button>

          <AnimatePresence>
            {showFilter && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className="absolute right-0 top-full mt-2 w-64 bg-card border border-border rounded-2xl shadow-2xl z-50 p-4"
              >
                <div className="space-y-4">
                  <div>
                    <label className="text-[10px] font-bold uppercase text-muted tracking-wider block mb-2">
                      Risk Level
                    </label>
                    <div className="space-y-2">
                      {["Very High", "High", "Moderate", "Low"].map((l) => (
                        <label key={l} className="flex items-center gap-2 text-xs cursor-pointer font-medium">
                          <input
                            type="checkbox"
                            checked={filterSeverity.includes(l)}
                            onChange={(e) => {
                              if (e.target.checked) setFilterSeverity([...filterSeverity, l])
                              else setFilterSeverity(filterSeverity.filter((x) => x !== l))
                            }}
                            className="accent-primary rounded"
                          />
                          {l}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold uppercase text-muted tracking-wider block mb-2">
                      Status
                    </label>
                    <div className="space-y-2">
                      {["Active", "Acknowledged"].map((s) => (
                        <label key={s} className="flex items-center gap-2 text-xs cursor-pointer font-medium">
                          <input
                            type="checkbox"
                            checked={filterStatus.includes(s)}
                            onChange={(e) => {
                              if (e.target.checked) setFilterStatus([...filterStatus, s])
                              else setFilterStatus(filterStatus.filter((x) => x !== s))
                            }}
                            className="accent-primary rounded"
                          />
                          {s}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="pt-3 border-t border-border flex gap-2">
                    <button
                      onClick={() => setShowFilter(false)}
                      className="w-full bg-primary text-white text-xs font-bold py-2 rounded-xl hover:bg-primary/90"
                    >
                      Done
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-risk-very-high-bg border border-risk-very-high/30 rounded-2xl p-4 shadow-xs">
          <div className="text-[10px] font-bold uppercase tracking-wider text-risk-very-high mb-1">
            Very High Risk
          </div>
          <div className="text-3xl font-bold tracking-tight text-risk-very-high">{veryHighCount}</div>
        </div>

        <div className="bg-risk-high-bg border border-risk-high/30 rounded-2xl p-4 shadow-xs">
          <div className="text-[10px] font-bold uppercase tracking-wider text-risk-high mb-1">High Risk</div>
          <div className="text-3xl font-bold tracking-tight text-risk-high">{highCount}</div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-4 shadow-xs">
          <div className="text-[10px] font-bold uppercase tracking-wider text-risk-moderate mb-1">
            Moderate Risk
          </div>
          <div className="text-3xl font-bold tracking-tight text-risk-moderate">{moderateCount}</div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-4 shadow-xs">
          <div className="text-[10px] font-bold uppercase tracking-wider text-foreground mb-1">
            Total Active
          </div>
          <div className="text-3xl font-bold tracking-tight text-foreground">{totalActive}</div>
        </div>
      </div>

      {/* Alert Items List */}
      {filteredAlerts.length === 0 ? (
        <div className="bg-card rounded-2xl border border-border p-12 text-center space-y-3">
          <div className="size-12 rounded-full bg-muted-bg flex items-center justify-center mx-auto text-muted">
            <AlertCircle size={24} />
          </div>
          <h3 className="font-bold text-base text-foreground">
            No active alerts available for this region.
          </h3>
          <p className="text-xs text-muted max-w-md mx-auto">
            There are currently no risk warnings matching the selected filters for {selectedRegion}.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <AnimatePresence>
            {filteredAlerts.map((alert) => (
              <motion.div
                key={alert.id}
                layout
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96 }}
                className={`bg-card rounded-2xl border p-5 flex flex-col md:flex-row md:items-center gap-4 hover:-translate-y-0.5 hover:shadow-md transition-all group ${
                  alert.status === "Acknowledged"
                    ? "opacity-60 border-border"
                    : alert.level === "Very High"
                    ? "border-risk-very-high/40 shadow-[0_0_16px_rgba(239,68,68,0.08)]"
                    : alert.level === "High"
                    ? "border-risk-high/30"
                    : "border-border"
                }`}
              >
                <div
                  className={`size-12 rounded-2xl flex items-center justify-center shrink-0 ${
                    alert.status === "Acknowledged"
                      ? "bg-muted-bg text-muted"
                      : alert.level === "Very High"
                      ? "bg-risk-very-high/10 text-risk-very-high"
                      : alert.level === "High"
                      ? "bg-risk-high/10 text-risk-high"
                      : "bg-risk-moderate/10 text-risk-moderate"
                  }`}
                >
                  <AlertTriangle size={22} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3
                      className={`font-bold text-base sm:text-lg truncate text-foreground ${
                        alert.status === "Acknowledged" ? "line-through text-muted" : ""
                      }`}
                    >
                      {alert.location}
                    </h3>
                    {alert.status !== "Acknowledged" && <RiskBadge level={alert.level} />}
                  </div>
                  <p className="text-xs text-muted leading-relaxed mb-2">
                    {alert.description || `High landslide probability detected in ${alert.state}`}
                  </p>
                  <div className="text-xs text-muted flex flex-wrap items-center gap-3 font-medium">
                    <span>
                      Probability:{" "}
                      <strong className={alert.status === "Acknowledged" ? "text-muted" : "text-foreground"}>
                        {alert.prob}
                      </strong>
                    </span>
                    <span>·</span>
                    <span>{alert.time}</span>
                    <span>·</span>
                    <span className="flex items-center gap-1">
                      Status:
                      {alert.status === "Acknowledged" ? (
                        <span className="text-risk-low flex items-center gap-1 font-bold">
                          <CheckCircle2 size={13} /> Acknowledged
                        </span>
                      ) : (
                        <span className="text-risk-high font-bold">{alert.status}</span>
                      )}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-end md:self-center flex-wrap">
                  <button
                    onClick={() => onViewDetails(alert.locationId)}
                    className="px-4 py-2.5 text-xs font-bold border border-border rounded-xl bg-card hover:bg-muted-bg flex items-center gap-1.5 transition-colors shadow-xs"
                  >
                    <Eye size={15} /> View Details
                  </button>
                  {alert.status === "Active" && (
                    <>
                      <button
                        onClick={async () => {
                          setSmsLoading(alert.id)
                          try {
                            const data = await dispatchSMSAlert(alert)
                            setSmsResult({ alert, data })
                          } catch (err) {
                            setSmsResult({
                              alert,
                              data: {
                                demo_mode: true,
                                message_preview: `⚠️ LANDGUARD ALERT: ${alert.level} landslide risk at ${alert.location}, ${alert.state}. AI Probability: ${alert.prob}. Take immediate precautionary action.`,
                                recipients_count: 2,
                                integration_note: "Backend unreachable — SMS preview generated locally.",
                              },
                            })
                          } finally {
                            setSmsLoading(null)
                          }
                        }}
                        disabled={smsLoading === alert.id}
                        className="px-4 py-2.5 text-xs font-bold rounded-xl bg-amber-500 text-white hover:bg-amber-600 flex items-center gap-1.5 shadow-md shadow-amber-500/20 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        {smsLoading === alert.id ? (
                          <span className="size-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                        ) : (
                          <MessageSquare size={15} />
                        )}
                        Send SMS
                      </button>
                      <button
                        onClick={() => onAcknowledge(alert.id)}
                        className="px-4 py-2.5 text-xs font-bold rounded-xl bg-primary text-white hover:bg-primary/90 flex items-center gap-1.5 shadow-md shadow-primary/20 transition-all"
                      >
                        <CheckCircle2 size={15} /> Acknowledge
                      </button>
                    </>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* SMS Confirmation Modal */}
      <AnimatePresence>
        {smsResult && (
          <motion.div
            key="sms-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => setSmsResult(null)}
          >
            <motion.div
              initial={{ scale: 0.92, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.92, opacity: 0, y: 20 }}
              transition={{ type: "spring", stiffness: 300, damping: 24 }}
              className="bg-card border border-amber-500/30 rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="size-10 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center">
                    <MessageSquare size={20} />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-foreground">
                      {smsResult.data.demo_mode ? "SMS Alert (Demo)" : "SMS Alert Dispatched ✓"}
                    </h3>
                    <p className="text-[11px] text-muted">
                      {smsResult.data.recipients_count} recipient{smsResult.data.recipients_count !== 1 ? "s" : ""} · {smsResult.alert.state} DM Control Room
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSmsResult(null)}
                  className="text-muted hover:text-foreground transition-colors p-1"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Message Preview */}
              <div className="bg-muted-bg rounded-xl p-4 border border-border">
                <div className="text-[10px] font-bold uppercase tracking-wider text-muted mb-2">Message Preview</div>
                <p className="text-xs text-foreground leading-relaxed font-mono">
                  {smsResult.data.message_preview}
                </p>
              </div>

              {/* Status Tag */}
              <div className={`flex items-center gap-2 text-xs font-medium px-3 py-2 rounded-xl ${
                smsResult.data.demo_mode
                  ? "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                  : "bg-risk-low/10 text-risk-low border border-risk-low/20"
              }`}>
                <span className={`size-2 rounded-full ${
                  smsResult.data.demo_mode ? "bg-amber-500" : "bg-risk-low animate-pulse"
                }`} />
                {smsResult.data.integration_note}
              </div>

              <button
                onClick={() => setSmsResult(null)}
                className="w-full bg-primary text-white text-xs font-bold py-2.5 rounded-xl hover:bg-primary/90 transition-colors"
              >
                Close
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
