import React from "react"
import { motion } from "framer-motion"
import { Activity, Server, Database, Radio, CheckCircle2, ShieldCheck } from "lucide-react"

export default function ModelStatusView() {
  const statusItems = [
    { title: "Landslide XGBoost Model", status: "Online", latency: "14 ms", uptime: "99.98%" },
    { title: "Northeast GIS Telemetry Stream", status: "Updated", latency: "28 ms", uptime: "99.95%" },
    { title: "Risk Prediction Inference API", status: "Online", latency: "18 ms", uptime: "99.99%" },
    { title: "Tile Heatmap Service", status: "Online", latency: "22 ms", uptime: "100.0%" },
  ]

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
          <Activity className="text-primary" size={24} /> System Infrastructure & Model Status
        </h1>
        <p className="text-xs sm:text-sm text-muted mt-0.5">
          Real-Time Health Monitoring for Northeast India Early Warning Services
        </p>
      </div>

      {/* Health Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statusItems.map((item) => (
          <div key={item.title} className="bg-card border border-border p-5 rounded-2xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="size-2.5 rounded-full bg-risk-low animate-pulse"></span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-risk-low bg-risk-low/10 px-2 py-0.5 rounded-full">
                {item.status}
              </span>
            </div>
            <div>
              <h3 className="font-bold text-sm text-foreground">{item.title}</h3>
              <div className="text-xs text-muted mt-1">Latency: {item.latency}</div>
            </div>
            <div className="pt-2 border-t border-border flex justify-between text-[11px] font-semibold text-muted">
              <span>Uptime</span>
              <span className="text-foreground">{item.uptime}</span>
            </div>
          </div>
        ))}
      </div>

      {/* System Metrics */}
      <div className="bg-card rounded-2xl border border-border p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-foreground flex items-center gap-2 border-b border-border pb-3">
          <Server size={18} className="text-primary" /> Predictive Engine Infrastructure
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-muted-bg/50 rounded-xl border border-border space-y-1">
            <div className="text-xs text-muted font-bold flex items-center gap-1.5">
              <Database size={14} className="text-primary" /> GIS Dataset Storage
            </div>
            <div className="text-xl font-bold text-foreground">600,000 Points</div>
            <div className="text-[10px] text-muted">Covering 8 Northeast India States</div>
          </div>

          <div className="p-4 bg-muted-bg/50 rounded-xl border border-border space-y-1">
            <div className="text-xs text-muted font-bold flex items-center gap-1.5">
              <Radio size={14} className="text-risk-low" /> Real-Time Sensor Stream
            </div>
            <div className="text-xl font-bold text-foreground">1,248 Sensors Active</div>
            <div className="text-[10px] text-muted">Precipitation & Moisture Probes</div>
          </div>

          <div className="p-4 bg-muted-bg/50 rounded-xl border border-border space-y-1">
            <div className="text-xs text-muted font-bold flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-primary" /> Warning Broadcast Pipeline
            </div>
            <div className="text-xl font-bold text-foreground">Sub-second Alert Relay</div>
            <div className="text-[10px] text-muted">Direct SDRF Broadcast Channel</div>
          </div>
        </div>
      </div>
    </div>
  )
}
