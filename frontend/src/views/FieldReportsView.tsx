import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Flag, Upload, CheckCircle2, AlertTriangle, MapPin, Camera } from "lucide-react"
import { FieldReport, RiskLevel } from "../types"
import RiskBadge from "../components/common/RiskBadge"

export default function FieldReportsView({
  reports,
  onAddReport,
  addToast,
}: {
  reports: FieldReport[]
  onAddReport: (rep: FieldReport) => void
  addToast: (msg: string, type?: "success" | "error") => void
}) {
  const [locationName, setLocationName] = useState("")
  const [stateName, setStateName] = useState("Arunachal Pradesh")
  const [hazardType, setHazardType] = useState<FieldReport["hazardType"]>("Slope Movement")
  const [severity, setSeverity] = useState<RiskLevel>("High")
  const [description, setDescription] = useState("")
  const [reporterName, setReporterName] = useState("Local Citizen / SDRF Volunteer")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!locationName || !description) {
      addToast("Please fill in location and description", "error")
      return
    }

    const newReport: FieldReport = {
      id: `REP-2026-00${reports.length + 1}`,
      locationName,
      state: stateName,
      lat: 26.5 + (Math.random() - 0.5) * 2,
      lon: 92.5 + (Math.random() - 0.5) * 3,
      hazardType,
      severity,
      description,
      photoUrl: "https://images.unsplash.com/photo-1541888946425-d0fbb186a5b3?w=800&auto=format",
      reporterName,
      timestamp: "Just now",
      status: "Pending Verification",
    }

    onAddReport(newReport)
    addToast("Field hazard report submitted successfully!")
    setLocationName("")
    setDescription("")
  }

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
          <Flag className="text-primary" size={24} /> Report a Landslide / Hazard
        </h1>
        <p className="text-xs sm:text-sm text-muted mt-0.5">
          Crowdsourced Community & SDRF Patrol Early Warning Field Intelligence
        </p>
      </div>

      {/* Quick Hazard Action Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { type: "Slope Movement", label: "Report Slope Movement", icon: "⛰️" },
          { type: "Road Crack", label: "Report Fissure / Crack", icon: "🛣️" },
          { type: "Rockfall", label: "Report Rockfall", icon: "🪨" },
          { type: "Mudslide", label: "Report Mudslide", icon: "🌧️" },
        ].map((item) => (
          <button
            key={item.type}
            onClick={() => setHazardType(item.type as FieldReport["hazardType"])}
            className={`p-4 rounded-2xl border text-left transition-all ${
              hazardType === item.type
                ? "bg-primary/10 border-primary text-primary font-bold shadow-sm"
                : "bg-card border-border hover:bg-muted-bg text-foreground font-semibold"
            }`}
          >
            <div className="text-2xl mb-1">{item.icon}</div>
            <div className="text-xs">{item.label}</div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-2 bg-card rounded-2xl border border-border p-6 shadow-sm">
          <h2 className="text-base font-bold text-foreground mb-4 flex items-center gap-2">
            <Camera size={18} className="text-primary" /> Submit Hazard Observation
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold uppercase text-muted tracking-wider block mb-1.5">
                  Location / Highway Stretch *
                </label>
                <input
                  type="text"
                  required
                  value={locationName}
                  onChange={(e) => setLocationName(e.target.value)}
                  placeholder="e.g. NH-415 Papum Pare Stretch"
                  className="w-full bg-muted-bg/60 border border-border rounded-xl px-3.5 py-2.5 text-xs font-medium focus:ring-1 focus:ring-primary outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold uppercase text-muted tracking-wider block mb-1.5">
                  State *
                </label>
                <select
                  value={stateName}
                  onChange={(e) => setStateName(e.target.value)}
                  className="w-full bg-muted-bg/60 border border-border rounded-xl px-3.5 py-2.5 text-xs font-bold focus:ring-1 focus:ring-primary outline-none cursor-pointer"
                >
                  {[
                    "Arunachal Pradesh",
                    "Assam",
                    "Manipur",
                    "Meghalaya",
                    "Mizoram",
                    "Nagaland",
                    "Sikkim",
                    "Tripura",
                  ].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold uppercase text-muted tracking-wider block mb-1.5">
                  Hazard Classification
                </label>
                <select
                  value={hazardType}
                  onChange={(e) =>
                    setHazardType(e.target.value as FieldReport["hazardType"])
                  }
                  className="w-full bg-muted-bg/60 border border-border rounded-xl px-3.5 py-2.5 text-xs font-bold focus:ring-1 focus:ring-primary outline-none cursor-pointer"
                >
                  {["Slope Movement", "Road Crack", "Rockfall", "Debris Flow", "Mudslide"].map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold uppercase text-muted tracking-wider block mb-1.5">
                  Observed Severity Rating
                </label>
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as RiskLevel)}
                  className="w-full bg-muted-bg/60 border border-border rounded-xl px-3.5 py-2.5 text-xs font-bold focus:ring-1 focus:ring-primary outline-none cursor-pointer"
                >
                  {["Low", "Moderate", "High", "Very High"].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold uppercase text-muted tracking-wider block mb-1.5">
                Detailed Observation & Description *
              </label>
              <textarea
                required
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe visible cracks, slope slumping, road blockages, rolling boulders, or water seepages..."
                className="w-full bg-muted-bg/60 border border-border rounded-xl p-3.5 text-xs font-medium focus:ring-1 focus:ring-primary outline-none resize-none"
              />
            </div>

            {/* Photo Upload Simulation */}
            <div className="border-2 border-dashed border-border rounded-2xl p-6 text-center bg-muted-bg/30">
              <Upload className="mx-auto text-primary mb-2" size={24} />
              <div className="text-xs font-bold text-foreground">Attach Photo Evidence / Location Geo-Tag</div>
              <div className="text-[10px] text-muted mt-1">Supports JPG, PNG, HEIC up to 10MB</div>
              <button
                type="button"
                onClick={() => addToast("Sample photo geo-tagged with GPS coordinates")}
                className="mt-3 text-xs bg-card border border-border font-bold px-3 py-1.5 rounded-xl hover:bg-muted-bg transition"
              >
                Simulate Photo Upload + GPS Tag
              </button>
            </div>

            <button
              type="submit"
              className="w-full py-3 bg-primary hover:bg-primary/90 text-white font-bold text-xs rounded-xl shadow-md shadow-primary/20 transition flex items-center justify-center gap-2 uppercase tracking-wider"
            >
              <CheckCircle2 size={16} /> Submit Field Report
            </button>
          </form>
        </div>

        {/* Recent Reports List */}
        <div className="bg-card rounded-2xl border border-border p-6 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-foreground flex items-center gap-2 border-b border-border pb-3">
            <Flag size={18} className="text-primary" /> Recent Community Reports
          </h2>

          <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
            {reports.map((rep) => (
              <div key={rep.id} className="p-3.5 bg-muted-bg/50 rounded-xl border border-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-muted">{rep.id}</span>
                  <RiskBadge level={rep.severity} small />
                </div>
                <div className="font-bold text-xs text-foreground flex items-center gap-1">
                  <MapPin size={12} className="text-primary" /> {rep.locationName}
                </div>
                <p className="text-[11px] text-muted line-clamp-2 leading-relaxed">{rep.description}</p>
                <div className="flex items-center justify-between text-[10px] text-muted pt-1 border-t border-border">
                  <span>{rep.reporterName}</span>
                  <span className="font-semibold text-primary">{rep.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
