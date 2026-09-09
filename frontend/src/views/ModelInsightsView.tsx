import React from "react"
import { motion } from "framer-motion"
import { BarChart2, Cpu, CheckCircle2, ShieldAlert, Sparkles } from "lucide-react"

export default function ModelInsightsView() {
  const metrics = [
    { label: "Accuracy", value: "94.2%", subtitle: "Across 1,248 sensors" },
    { label: "Precision", value: "92.8%", subtitle: "Low false alarm rate" },
    { label: "Recall", value: "91.6%", subtitle: "High hazard capture" },
    { label: "F1 Score", value: "92.2%", subtitle: "Harmonic balanced" },
  ]

  const featureImportances = [
    { name: "24h Rainfall Intensity", percent: 31, color: "#3B82F6" },
    { name: "Soil Moisture Saturation", percent: 24, color: "#10B981" },
    { name: "Slope Gradient / Angle", percent: 18, color: "#F59E0B" },
    { name: "Historical Landslide Events", percent: 12, color: "#EF4444" },
    { name: "Elevation Altitude", percent: 8, color: "#8B5CF6" },
    { name: "Land Cover Classification", percent: 4, color: "#EC4899" },
    { name: "Geology & Soil Type", percent: 3, color: "#64748B" },
  ]

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
          <BarChart2 className="text-primary" size={24} /> AI Model Insights & Feature Importance
        </h1>
        <p className="text-xs sm:text-sm text-muted mt-0.5">
          Explainable AI Architecture — Landslide-XGBoost Classifier v4.2
        </p>
      </div>

      {/* Model Performance Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="bg-card border border-border p-5 rounded-2xl shadow-xs">
            <div className="text-[10px] font-bold uppercase tracking-wider text-muted mb-1">{m.label}</div>
            <div className="text-3xl font-extrabold text-foreground tracking-tight">{m.value}</div>
            <div className="text-xs text-muted mt-1">{m.subtitle}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Feature Importance Chart */}
        <div className="lg:col-span-2 bg-card rounded-2xl border border-border p-6 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-foreground flex items-center gap-2 border-b border-border pb-3">
            <Cpu size={18} className="text-primary" /> Feature Importance Ranking (SHAP & Gini Index)
          </h2>

          <div className="space-y-4">
            {featureImportances.map((item) => (
              <div key={item.name} className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-foreground">{item.name}</span>
                  <span className="font-bold font-mono">{item.percent}%</span>
                </div>
                <div className="h-2.5 w-full bg-muted-bg rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${item.percent}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Explainability Card */}
        <div className="bg-card rounded-2xl border border-border p-6 shadow-sm flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-base font-bold text-foreground flex items-center gap-2 border-b border-border pb-3">
              <Sparkles size={18} className="text-primary" /> AI Explainability Insight
            </h2>

            <div className="bg-primary/5 p-4 rounded-xl border border-primary/20 mt-4 space-y-3">
              <div className="font-bold text-xs text-primary uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 size={14} /> How the Model Decides
              </div>
              <p className="text-xs text-muted leading-relaxed">
                The **Landslide-XGBoost v4.2** gradient boosted decision tree model combines real-time precipitation streams with static GIS layers (Digital Elevation Models, slope, aspect, distance to rivers, land cover).
              </p>
              <p className="text-xs text-muted leading-relaxed">
                Rainfall and soil saturation trigger over 55% of the risk weight. When slope exceeds 28° in high-rainfall zones, prediction probability spikes into the **Very High Risk** zone (&gt;80%).
              </p>
            </div>
          </div>

          <div className="p-4 bg-muted-bg rounded-xl border border-border text-xs space-y-1">
            <div className="font-bold text-foreground">Model Version: v4.2-NE-India</div>
            <div className="text-muted text-[11px]">Trained on: 600K GIS expanded records</div>
            <div className="text-muted text-[11px]">Cross-Validation: 10-Fold Stratified K-Fold</div>
          </div>
        </div>
      </div>
    </div>
  )
}
