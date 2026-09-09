import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Activity,
  X,
  Compass,
  TrendingUp,
  BarChart2,
  Info,
  Globe,
  CheckCircle2,
  Bell,
  History,
  Share2,
} from "lucide-react"
import { LocationData } from "../../types"
import FactorBar from "../common/FactorBar"
import GisCard from "../common/GisCard"

const RISK_COLORS: Record<string, string> = {
  Low: "#10B981",
  Moderate: "#F59E0B",
  High: "#F97316",
  "Very High": "#EF4444",
}

export default function LocationRiskDetailsDrawer({
  location,
  onClose,
  addToast,
}: {
  location: LocationData
  onClose: () => void
  addToast: (msg: string, type?: "success" | "error") => void
}) {
  const [showExplanation, setShowExplanation] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [subscribed, setSubscribed] = useState(false)

  const color = RISK_COLORS[location.risk] || "#10B981"
  const trendData =
    location.risk === "Very High"
      ? [52, 58, 64, 71, 79, location.prob]
      : location.risk === "High"
      ? [42, 48, 53, 59, 65, location.prob]
      : [28, 33, 37, 40, 42, location.prob]

  return (
    <motion.div
      initial={{ x: "100%", opacity: 0.8 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: "100%", opacity: 0.8 }}
      transition={{ type: "spring", damping: 28, stiffness: 220 }}
      className="absolute top-0 right-0 bottom-0 w-full sm:w-[420px] bg-card border-l border-border shadow-2xl flex flex-col z-[500] overflow-hidden"
    >
      {/* Header */}
      <div className="px-5 py-3.5 bg-muted-bg/50 border-b border-border flex items-center justify-between shrink-0">
        <h3 className="text-[10px] font-bold tracking-widest text-muted uppercase flex items-center gap-2">
          <Activity size={13} className="text-primary" /> Location Risk Analysis
        </h3>
        <button
          onClick={onClose}
          className="text-muted hover:text-foreground p-1.5 rounded-lg hover:bg-card border border-transparent hover:border-border transition-colors"
        >
          <X size={15} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-5 space-y-5">
          {/* Location Meta */}
          <div>
            <h2 className="text-xl font-bold text-foreground leading-snug">{location.name}</h2>
            <div className="text-xs font-mono text-muted flex items-center gap-3 mt-1">
              <span className="flex items-center gap-1">
                <Compass size={11} /> {location.lat.toFixed(4)}°N
              </span>
              <span>{location.lon.toFixed(4)}°E</span>
              <span className="text-[10px] font-semibold text-primary">{location.district}</span>
            </div>
            <div className="text-[10px] text-muted/70 mt-1 flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-risk-low inline-block animate-pulse"></span>
              Live telemetry updated 2 mins ago
            </div>
          </div>

          {/* Circular Risk Gauge */}
          <div className="flex flex-col items-center py-2">
            <div className="relative size-32 mb-3">
              <svg className="size-full rotate-[-90deg]" viewBox="0 0 36 36">
                <path
                  fill="none"
                  strokeWidth="3"
                  stroke={color + "22"}
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <motion.path
                  initial={{ strokeDasharray: "0, 100" }}
                  animate={{ strokeDasharray: `${location.prob}, 100` }}
                  transition={{ duration: 1.4, ease: "easeOut" }}
                  fill="none"
                  strokeWidth="3"
                  stroke={color}
                  strokeLinecap="round"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <motion.span
                  initial={{ opacity: 0, scale: 0.7 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-4xl font-bold tracking-tighter"
                  style={{ color }}
                >
                  {location.prob}%
                </motion.span>
                <span className="text-[9px] font-bold text-muted uppercase tracking-wider">AI Probability</span>
              </div>
            </div>

            <div
              className="text-white text-xs font-bold px-6 py-2 rounded-full tracking-widest shadow-lg uppercase"
              style={{ backgroundColor: color, boxShadow: `0 4px 16px ${color}55` }}
            >
              {location.risk} Risk
            </div>
          </div>

          {/* 24h Risk Trend */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted mb-2.5 flex items-center gap-2">
              <TrendingUp size={12} style={{ color }} /> Risk Trend — Last 24 Hours
            </h4>
            <RiskTrendChart data={trendData} color={color} />
          </div>

          {/* Major Contributing Factors */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider mb-3 flex items-center justify-between border-b border-border pb-2">
              <span className="flex items-center gap-2">
                <BarChart2 size={12} className="text-primary" /> AI Contributing Factors
              </span>
              <span className="text-[10px] font-normal text-muted bg-muted-bg px-2 py-0.5 rounded-full border border-border">
                SHAP Importance
              </span>
            </h4>
            <div className="space-y-3">
              <FactorBar label="24h Rainfall" percent={31} value={`${location.rainfall24h} mm`} />
              <FactorBar label="Soil Moisture Saturation" percent={24} value={`${location.soilMoisture}%`} />
              <FactorBar label="Slope Steepness" percent={18} value={`${location.slope}°`} />
              <FactorBar label="Historical Susceptibility" percent={12} value={`${location.historicalNearby} events`} />
              <FactorBar label="Elevation" percent={8} value={`${location.elevation} m`} />
            </div>

            <button
              onClick={() => setShowExplanation(!showExplanation)}
              className="w-full mt-4 py-2.5 text-xs font-bold rounded-xl border border-primary/30 bg-primary/5 hover:bg-primary/10 text-primary transition flex items-center justify-center gap-2"
            >
              <Info size={13} /> WHY THIS RISK?
            </button>

            <AnimatePresence>
              {showExplanation && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden mt-3"
                >
                  <div className="bg-primary/5 p-4 rounded-xl border border-primary/20">
                    <div className="font-bold text-xs text-primary uppercase tracking-wide mb-2 flex items-center gap-1.5">
                      <Info size={12} /> AI XGBoost Explanation
                    </div>
                    <p className="text-xs text-muted leading-relaxed">
                      Sustained 24h precipitation ({location.rainfall24h}mm) paired with elevated soil moisture saturation ({location.soilMoisture}%) on steep mountain topography ({location.slope}°) significantly increases slip shear stress. {location.historicalNearby} recorded historical landslides nearby confirm this slope as a high-vulnerability landslide hazard zone in {location.state}.
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* GIS Features */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider mb-3 border-b border-border pb-2 flex items-center gap-2">
              <Globe size={12} className="text-muted" /> GIS Environmental Features
            </h4>
            <div className="grid grid-cols-2 gap-2.5">
              <GisCard label="Elevation" value={`${location.elevation} m`} />
              <GisCard label="Slope" value={`${location.slope}°`} />
              <GisCard label="Aspect" value={`${location.aspect}°`} />
              <GisCard label="Curvature" value={`${location.curvature}`} />
              <GisCard label="Dist to River" value={`${location.riverDist} m`} />
              <GisCard label="Land Cover" value={location.landCover} />
              <GisCard label="Soil Type" value={location.soilType} />
              <GisCard label="Geology" value={location.geology} />
            </div>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-border shrink-0 bg-card shadow-[0_-8px_30px_rgba(0,0,0,0.05)]">
        <div className="flex flex-col gap-2.5">
          <button
            onClick={() => {
              if (!subscribed) {
                setSubscribed(true)
                addToast(`Subscribed to landslide risk alerts for ${location.shortName}`)
              }
            }}
            className={`w-full font-bold py-3 rounded-xl transition flex items-center justify-center gap-2 text-xs uppercase tracking-wider ${
              subscribed
                ? "bg-risk-low/10 text-risk-low border border-risk-low/20 cursor-default"
                : "bg-primary hover:bg-primary/90 text-white shadow-md shadow-primary/20"
            }`}
          >
            {subscribed ? (
              <>
                <CheckCircle2 size={15} /> Subscribed to Alerts ✓
              </>
            ) : (
              <>
                <Bell size={15} /> Subscribe to Location Alerts
              </>
            )}
          </button>
          <div className="grid grid-cols-2 gap-2.5">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="py-2.5 text-xs font-bold rounded-xl border border-border bg-card hover:bg-muted-bg transition flex items-center justify-center gap-1.5"
            >
              <History size={13} /> {showHistory ? "Hide History" : "View History"}
            </button>
            <button
              onClick={() => addToast(`Risk report for ${location.name} copied to clipboard`)}
              className="py-2.5 text-xs font-bold rounded-xl border border-border bg-card hover:bg-muted-bg transition flex items-center justify-center gap-1.5"
            >
              <Share2 size={13} /> Share Report
            </button>
          </div>
        </div>

        <AnimatePresence>
          {showHistory && (
            <motion.div
              initial={{ opacity: 0, height: 0, marginTop: 0 }}
              animate={{ opacity: 1, height: "auto", marginTop: 12 }}
              exit={{ opacity: 0, height: 0, marginTop: 0 }}
              className="overflow-hidden"
            >
              <div className="bg-muted-bg rounded-xl border border-border p-4">
                <div className="text-[10px] font-bold uppercase text-muted tracking-wider mb-3">
                  Historical Events near {location.shortName}
                </div>
                <div className="space-y-3 relative before:absolute before:inset-y-0 before:left-1.5 before:w-px before:bg-border">
                  {[
                    { year: 2024, dist: "420 m", trigger: "Extreme Monsoon Downpour" },
                    { year: 2023, dist: "680 m", trigger: "Slope Bank Collapse" },
                    { year: 2021, dist: "1.2 km", trigger: "Cloudburst" },
                  ].map((evt) => (
                    <div key={evt.year} className="relative pl-6 text-xs">
                      <div className="absolute left-0 top-1 size-3 bg-muted border-2 border-background rounded-sm rotate-45"></div>
                      <div className="font-bold text-foreground">Landslide Event — {evt.year}</div>
                      <div className="text-[11px] text-muted">
                        {evt.dist} distance · {evt.trigger}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

function RiskTrendChart({ data, color }: { data: number[]; color: string }) {
  const W = 340
  const H = 64
  const pad = { l: 6, r: 6, t: 8, b: 14 }
  const cw = W - pad.l - pad.r
  const ch = H - pad.t - pad.b
  const mn = Math.min(...data) - 8
  const mx = Math.max(...data) + 5

  const pts = data.map((v, i) => ({
    x: pad.l + (i / (data.length - 1)) * cw,
    y: pad.t + (1 - (v - mn) / (mx - mn)) * ch,
  }))

  const line = pts.reduce((d, p, i) => {
    if (i === 0) return `M${p.x} ${p.y}`
    const prev = pts[i - 1]
    const mx2 = (prev.x + p.x) / 2
    return `${d} C${mx2} ${prev.y} ${mx2} ${p.y} ${p.x} ${p.y}`
  }, "")

  const area = `${line} L${pts[pts.length - 1].x} ${H - pad.b} L${pts[0].x} ${H - pad.b} Z`
  const gradId = `tg-${color.replace("#", "")}`
  const times = ["00:00", "04:00", "08:00", "12:00", "18:00", "Now"]

  return (
    <div className="bg-muted-bg/60 rounded-xl p-3 border border-border">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-16">
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <motion.path d={area} fill={`url(#${gradId})`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} />
        <motion.path
          d={line}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
        {pts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={i === pts.length - 1 ? 3.5 : 2} fill={color} />
        ))}
        {times.map((t, i) => (
          <text
            key={i}
            x={pts[i].x}
            y={H - 2}
            textAnchor="middle"
            fontSize="7"
            fill="#64748B"
            style={{ fontFamily: "monospace" }}
          >
            {t}
          </text>
        ))}
      </svg>
    </div>
  )
}
