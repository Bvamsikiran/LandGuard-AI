import React, { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Layers, ChevronRight, TrendingUp, TrendingDown, ArrowUpRight, AlertCircle } from "lucide-react"
import { LocationData, Alert } from "../types"
import StatCard from "../components/common/StatCard"
import RiskBadge from "../components/common/RiskBadge"

export default function DashboardView({
  locations,
  alerts,
  selectedRegion,
  onNavigateToMap,
}: {
  locations: LocationData[]
  alerts: Alert[]
  selectedRegion: string
  onNavigateToMap: (locationId?: number) => void
}) {
  // Strict Region Filtering
  const regionLocations =
    selectedRegion === "Northeastern India"
      ? locations
      : locations.filter((l) => l.state.toLowerCase() === selectedRegion.toLowerCase())

  const regionAlerts =
    selectedRegion === "Northeastern India"
      ? alerts
      : alerts.filter((a) => a.state.toLowerCase() === selectedRegion.toLowerCase())

  const activeAlertsCount = regionAlerts.filter((a) => a.status === "Active").length
  const veryHighAlertsCount = regionAlerts.filter((a) => a.level === "Very High" && a.status === "Active").length
  const highAlertsCount = regionAlerts.filter((a) => a.level === "High" && a.status === "Active").length

  const [animCount, setAnimCount] = useState({ alerts: 0, locations: 0 })

  useEffect(() => {
    const steps = 30
    let step = 0
    const timer = setInterval(() => {
      step++
      const ease = 1 - Math.pow(1 - Math.min(1, step / steps), 3)
      setAnimCount({
        alerts: Math.round(activeAlertsCount * ease),
        locations: Math.round(regionLocations.length * 104 * ease),
      })
      if (step >= steps) clearInterval(timer)
    }, 800 / steps)
    return () => clearInterval(timer)
  }, [activeAlertsCount, regionLocations.length])

  const highRiskLocs = regionLocations
    .filter((l) => l.risk === "Very High" || l.risk === "High")
    .slice(0, 4)

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="text-2xl font-bold text-foreground tracking-tight">System Overview</h2>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            AI-Powered Landslide Risk Monitoring — {selectedRegion}
          </p>
        </div>
        <span className="text-xs text-muted bg-card px-3 py-1.5 rounded-full border border-border font-medium shadow-xs self-start sm:self-auto">
          Telemetry Update: Today, Live IST
        </span>
      </div>

      {/* Stat Cards - Consistent Numbers */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Overall Risk Level"
          value={veryHighAlertsCount > 0 ? "Elevated" : "Moderate"}
          subtitle={`${regionLocations.length} locations monitored`}
          risk={veryHighAlertsCount > 0 ? "high" : "moderate"}
          trend={selectedRegion === "Northeastern India" ? "↑ 12% 24h" : `${selectedRegion}`}
          trendType="bad"
        />
        <StatCard
          title="Active Alerts"
          value={animCount.alerts.toString()}
          subtitle={`${veryHighAlertsCount} Very High · ${highAlertsCount} High`}
          risk="high"
          trend="↑ Live Sensor"
          trendType="bad"
        />
        <StatCard
          title="Locations Monitored"
          value={regionLocations.length > 0 ? animCount.locations.toLocaleString() : "0"}
          subtitle={selectedRegion}
          risk="low"
          trend="↑ Monitored"
          trendType="neutral"
        />
        <StatCard
          title="Model Status"
          value="Active"
          subtitle="94.2% XGBoost Accuracy"
          risk="low"
          isStatus
        />
      </div>

      {/* Main Grid: Map Thumbnail & High Risk Table */}
      {regionLocations.length === 0 ? (
        <div className="bg-card rounded-2xl border border-border p-12 text-center space-y-3">
          <div className="size-12 rounded-full bg-muted-bg flex items-center justify-center mx-auto text-muted">
            <AlertCircle size={24} />
          </div>
          <h3 className="font-bold text-base text-foreground">
            No monitored locations available for this region.
          </h3>
          <p className="text-xs text-muted max-w-md mx-auto">
            Currently displaying active telemetry data for Northeast India. Select another state or "Northeastern India" from the region header dropdown.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-auto lg:h-[420px]">
          {/* Map Preview Thumbnail */}
          <div className="lg:col-span-2 bg-card rounded-2xl border border-border shadow-sm flex flex-col overflow-hidden relative group">
            <div className="absolute top-0 left-0 right-0 p-5 flex items-center justify-between z-10 bg-gradient-to-b from-slate-900/90 to-transparent text-white">
              <h2 className="font-semibold text-base sm:text-lg flex items-center gap-2">
                <Layers size={17} className="text-primary" /> Risk Heatmap Preview · {selectedRegion}
              </h2>
              <button
                onClick={() => onNavigateToMap()}
                className="text-xs font-bold bg-primary hover:bg-primary/90 text-white px-3 py-1.5 rounded-xl transition flex items-center gap-1 shadow-md"
              >
                Open Full Map <ChevronRight size={14} />
              </button>
            </div>

            <div
              className="flex-1 relative cursor-pointer min-h-[260px] bg-slate-900"
              onClick={() => onNavigateToMap()}
            >
              <div
                className="absolute inset-0 bg-cover bg-center opacity-85 group-hover:scale-105 transition-transform duration-700"
                style={{
                  backgroundImage:
                    "url('https://images.unsplash.com/photo-1652792595182-427510e8644f?w=1600&auto=format')",
                }}
              ></div>
              <div className="absolute inset-0 bg-slate-900/40 mix-blend-multiply"></div>

              {/* Dynamic dots for region */}
              {regionLocations.slice(0, 6).map((loc, i) => (
                <div
                  key={loc.id}
                  className="absolute z-10"
                  style={{
                    left: `${20 + (i * 14) % 70}%`,
                    top: `${25 + (i * 12) % 55}%`,
                  }}
                >
                  <div
                    className="size-3.5 rounded-full border-2 border-white animate-pulse"
                    style={{
                      backgroundColor:
                        loc.risk === "Very High"
                          ? "#EF4444"
                          : loc.risk === "High"
                          ? "#F97316"
                          : "#F59E0B",
                      boxShadow: "0 0 12px currentColor",
                    }}
                  ></div>
                </div>
              ))}

              <div className="absolute bottom-4 left-4 right-4 flex flex-wrap items-end justify-between gap-3 z-10">
                <div className="bg-card/90 backdrop-blur-md border border-border p-3 rounded-xl shadow-lg">
                  <div className="text-[10px] font-bold text-muted uppercase tracking-wider mb-1.5">
                    Risk Status Legend
                  </div>
                  <div className="flex gap-3">
                    {[
                      { label: "Low", color: "#10B981" },
                      { label: "Moderate", color: "#F59E0B" },
                      { label: "High", color: "#F97316" },
                      { label: "Very High", color: "#EF4444" },
                    ].map((r) => (
                      <div key={r.label} className="flex items-center gap-1 text-xs font-semibold">
                        <span className="size-2 rounded-full" style={{ backgroundColor: r.color }}></span>
                        <span>{r.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-risk-very-high text-white px-3.5 py-2 rounded-xl text-xs font-bold shadow-lg flex items-center gap-1.5">
                  <span>{activeAlertsCount} Active High-Risk Alerts</span>
                  <ArrowUpRight size={14} />
                </div>
              </div>
            </div>
          </div>

          {/* High Risk Locations Sidebar */}
          <div className="bg-card rounded-2xl border border-border shadow-sm flex flex-col overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-border flex items-center justify-between">
              <div>
                <h2 className="font-bold text-base text-foreground">Recent High-Risk</h2>
                <p className="text-[11px] text-muted">{selectedRegion} Monitored Zones</p>
              </div>
              <button
                onClick={() => onNavigateToMap()}
                className="text-xs text-primary font-bold hover:underline"
              >
                View All
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-muted-bg/30">
              {highRiskLocs.length === 0 ? (
                <div className="p-6 text-center text-xs text-muted font-medium">
                  No high risk locations reported in {selectedRegion}.
                </div>
              ) : (
                highRiskLocs.map((loc) => (
                  <div
                    key={loc.id}
                    className="bg-card p-3.5 rounded-xl border border-border shadow-xs flex items-center justify-between hover:border-primary/40 hover:shadow-md transition-all cursor-pointer group"
                    onClick={() => onNavigateToMap(loc.id)}
                  >
                    <div>
                      <div className="font-bold text-xs text-foreground mb-1 group-hover:text-primary transition-colors">
                        {loc.name}
                      </div>
                      <div className="flex items-center gap-2">
                        <RiskBadge level={loc.risk} small />
                        <span className="text-xs font-mono font-bold text-muted">{loc.prob}% risk</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span
                        className={`text-[10px] font-bold flex items-center gap-0.5 ${
                          loc.change.startsWith("+") ? "text-risk-high" : "text-risk-low"
                        }`}
                      >
                        {loc.change.startsWith("+") ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                        {loc.change}
                      </span>
                      <ChevronRight size={14} className="text-muted group-hover:text-primary transition-colors" />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
