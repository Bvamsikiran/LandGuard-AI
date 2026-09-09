import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Settings,
  Save,
  RotateCcw,
  Bell,
  Globe,
  Sun,
  Moon,
  Laptop,
  Check,
  AlertTriangle,
  Radio,
  Cpu,
  Server,
  Layers,
} from "lucide-react"
import { AppSettings, MapStyle, ThemeMode, RiskLevel } from "../types"
import { DEFAULT_SETTINGS } from "../data/northeast_dataset"

export default function SettingsView({
  settings,
  onSaveSettings,
  addToast,
}: {
  settings: AppSettings
  onSaveSettings: (newSettings: AppSettings) => void
  addToast: (msg: string, type?: "success" | "error") => void
}) {
  const [localSettings, setLocalSettings] = useState<AppSettings>(settings)
  const [showResetModal, setShowResetModal] = useState(false)

  const handleSave = () => {
    onSaveSettings(localSettings)
    addToast("✓ Settings saved successfully")
  }

  const handleConfirmReset = () => {
    setLocalSettings(DEFAULT_SETTINGS)
    onSaveSettings(DEFAULT_SETTINGS)
    setShowResetModal(false)
    addToast("✓ Settings restored to default")
  }

  const handleThemeSelect = (theme: ThemeMode) => {
    const updated = {
      ...localSettings,
      appearance: { ...localSettings.appearance, theme },
    }
    setLocalSettings(updated)
    onSaveSettings(updated)
    addToast(`Theme set to ${theme.toUpperCase()}`)
  }

  return (
    <div className="p-6 sm:p-8 max-w-6xl mx-auto space-y-6 animate-in fade-in duration-300 pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <Settings className="text-primary" size={24} /> Application Settings
          </h1>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            Configure LANDGUARD AI monitoring, map, alerts and interface preferences.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          <button
            onClick={() => setShowResetModal(true)}
            className="px-4 py-2.5 text-xs font-bold border border-border rounded-xl bg-card hover:bg-muted-bg text-foreground flex items-center gap-1.5 transition shadow-xs cursor-pointer"
          >
            <RotateCcw size={14} /> Reset
          </button>
          <button
            onClick={handleSave}
            className="px-5 py-2.5 text-xs font-bold rounded-xl bg-primary text-white hover:bg-primary/90 flex items-center gap-1.5 shadow-md shadow-primary/20 transition uppercase tracking-wider cursor-pointer"
          >
            <Save size={14} /> Save Changes
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 1: 🔔 Notifications */}
        <div className="bg-card rounded-2xl border border-border p-6 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2 border-b border-border pb-3 uppercase tracking-wider">
            <Bell size={16} className="text-primary" /> Notification Preferences
          </h2>

          <div className="space-y-3">
            {[
              {
                key: "pushAlerts",
                label: "Browser Push Risk Notifications",
                desc: "Real-time alerts for elevated risk zones",
              },
              {
                key: "emailAlerts",
                label: "Email Emergency Alerts",
                desc: "Send high-risk warnings to registered email",
              },
              {
                key: "criticalOnly",
                label: "Very High Risk Only",
                desc: "Only notify for critical events",
              },
              {
                key: "soundEnabled",
                label: "Alert Audio Warning Chime",
                desc: "Play sound effect when critical alert is received",
              },
            ].map((item) => {
              const checked =
                localSettings.notifications[
                  item.key as keyof AppSettings["notifications"]
                ]
              return (
                <div
                  key={item.key}
                  onClick={() =>
                    setLocalSettings({
                      ...localSettings,
                      notifications: {
                        ...localSettings.notifications,
                        [item.key]: !checked,
                      },
                    })
                  }
                  className="flex items-center justify-between p-3.5 bg-muted-bg/40 hover:bg-muted-bg/80 rounded-xl border border-border cursor-pointer transition-colors"
                >
                  <div>
                    <div className="text-xs font-bold text-foreground">{item.label}</div>
                    <div className="text-[11px] text-muted">{item.desc}</div>
                  </div>
                  {/* Modern Toggle Switch */}
                  <div
                    className={`w-9 h-5 rounded-full transition-colors relative shrink-0 ${
                      checked ? "bg-primary" : "bg-slate-300 dark:bg-slate-700"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 size-4 rounded-full bg-white shadow-sm transition-transform ${
                        checked ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Section 2: 🌐 GIS Map Preferences */}
        <div className="bg-card rounded-2xl border border-border p-6 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2 border-b border-border pb-3 uppercase tracking-wider">
            <Globe size={16} className="text-primary" /> GIS Map Preferences
          </h2>

          <div className="space-y-3.5">
            <div>
              <label className="text-xs font-bold text-muted uppercase tracking-wider block mb-1.5">
                Default Map Style
              </label>
              <select
                value={localSettings.map.defaultStyle}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    map: {
                      ...localSettings.map,
                      defaultStyle: e.target.value as MapStyle,
                    },
                  })
                }
                className="w-full bg-muted-bg/60 border border-border rounded-xl px-3.5 py-2.5 text-xs font-bold text-foreground outline-none cursor-pointer"
              >
                <option value="satellite">Satellite (Esri World Imagery)</option>
                <option value="terrain">Terrain (OpenTopoMap)</option>
                <option value="streets">Streets (OpenStreetMap)</option>
                <option value="light">Carto Light</option>
              </select>
            </div>

            {[
              { key: "autoRefresh", label: "Auto-refresh GIS Data" },
              { key: "showHeatmap", label: "Show Risk Heatmap" },
              { key: "showHistorical", label: "Show Historical Landslides" },
              { key: "showRivers", label: "Show Rivers" },
              { key: "showRoads", label: "Show Roads" },
              { key: "showTerrain", label: "Show Terrain" },
            ].map((item) => {
              const checked =
                localSettings.map[item.key as keyof AppSettings["map"]]
              return (
                <div
                  key={item.key}
                  onClick={() =>
                    setLocalSettings({
                      ...localSettings,
                      map: {
                        ...localSettings.map,
                        [item.key]: !checked,
                      },
                    })
                  }
                  className="flex items-center justify-between p-2.5 bg-muted-bg/40 hover:bg-muted-bg/80 rounded-xl border border-border cursor-pointer transition-colors"
                >
                  <span className="text-xs font-bold text-foreground">{item.label}</span>
                  <div
                    className={`w-9 h-5 rounded-full transition-colors relative shrink-0 ${
                      checked ? "bg-primary" : "bg-slate-300 dark:bg-slate-700"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 size-4 rounded-full bg-white shadow-sm transition-transform ${
                        checked ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Section 3: 🎯 Risk Monitoring */}
        <div className="bg-card rounded-2xl border border-border p-6 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2 border-b border-border pb-3 uppercase tracking-wider">
            <Radio size={16} className="text-primary" /> Risk Monitoring Thresholds
          </h2>

          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-bold text-muted uppercase tracking-wider block mb-1.5">
                  Default Risk Threshold
                </label>
                <select
                  value={localSettings.riskMonitoring.defaultThreshold}
                  onChange={(e) =>
                    setLocalSettings({
                      ...localSettings,
                      riskMonitoring: {
                        ...localSettings.riskMonitoring,
                        defaultThreshold: e.target.value as RiskLevel,
                      },
                    })
                  }
                  className="w-full bg-muted-bg/60 border border-border rounded-xl px-3.5 py-2 text-xs font-bold text-foreground outline-none cursor-pointer"
                >
                  <option value="Low">Low Risk</option>
                  <option value="Moderate">Moderate Risk</option>
                  <option value="High">High Risk</option>
                  <option value="Very High">Very High Risk</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-muted uppercase tracking-wider block mb-1.5">
                  Prediction Refresh Interval
                </label>
                <select
                  value={localSettings.riskMonitoring.predictionInterval}
                  onChange={(e) =>
                    setLocalSettings({
                      ...localSettings,
                      riskMonitoring: {
                        ...localSettings.riskMonitoring,
                        predictionInterval: e.target.value,
                      },
                    })
                  }
                  className="w-full bg-muted-bg/60 border border-border rounded-xl px-3.5 py-2 text-xs font-bold text-foreground outline-none cursor-pointer"
                >
                  <option value="1 minute">1 minute</option>
                  <option value="5 minutes">5 minutes</option>
                  <option value="15 minutes">15 minutes</option>
                  <option value="1 hour">1 hour</option>
                </select>
              </div>
            </div>

            {[
              { key: "showProbability", label: "Show Risk Probability Percentage" },
              { key: "showExplanations", label: "Show AI Model Explanations" },
            ].map((item) => {
              const checked =
                localSettings.riskMonitoring[
                  item.key as keyof AppSettings["riskMonitoring"]
                ]
              return (
                <div
                  key={item.key}
                  onClick={() =>
                    setLocalSettings({
                      ...localSettings,
                      riskMonitoring: {
                        ...localSettings.riskMonitoring,
                        [item.key]: !checked,
                      },
                    })
                  }
                  className="flex items-center justify-between p-3 bg-muted-bg/40 hover:bg-muted-bg/80 rounded-xl border border-border cursor-pointer transition-colors"
                >
                  <span className="text-xs font-bold text-foreground">{item.label}</span>
                  <div
                    className={`w-9 h-5 rounded-full transition-colors relative shrink-0 ${
                      checked ? "bg-primary" : "bg-slate-300 dark:bg-slate-700"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 size-4 rounded-full bg-white shadow-sm transition-transform ${
                        checked ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Section 4: 🎨 Appearance Theme Cards (Requirement #12) */}
        <div className="bg-card rounded-2xl border border-border p-6 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2 border-b border-border pb-3 uppercase tracking-wider">
            <Sun size={16} className="text-primary" /> Appearance Theme
          </h2>

          <div className="grid grid-cols-3 gap-3">
            {[
              {
                id: "light" as ThemeMode,
                icon: Sun,
                label: "LIGHT",
                desc: "Clean Studio UI",
              },
              {
                id: "dark" as ThemeMode,
                icon: Moon,
                label: "DARK",
                desc: "GIS Command",
              },
              {
                id: "system" as ThemeMode,
                icon: Laptop,
                label: "SYSTEM",
                desc: "Follow OS",
              },
            ].map((t) => {
              const Icon = t.icon
              const isSelected = localSettings.appearance.theme === t.id
              return (
                <div
                  key={t.id}
                  onClick={() => handleThemeSelect(t.id)}
                  className={`p-4 rounded-2xl border text-center cursor-pointer transition-all relative ${
                    isSelected
                      ? "border-primary bg-primary/10 shadow-md text-primary font-bold ring-2 ring-primary/40"
                      : "border-border bg-muted-bg/30 hover:bg-muted-bg text-foreground font-semibold"
                  }`}
                >
                  {isSelected && (
                    <div className="absolute top-2 right-2 size-4 rounded-full bg-primary text-white flex items-center justify-center">
                      <Check size={10} />
                    </div>
                  )}
                  <Icon size={24} className="mx-auto mb-2" />
                  <div className="text-xs font-bold">{t.label}</div>
                  <div className="text-[10px] text-muted mt-0.5">{t.desc}</div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Section 5: 🖥 System Status Card (Requirement #13) */}
      <div className="bg-card rounded-2xl border border-border p-6 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-foreground flex items-center justify-between border-b border-border pb-3 uppercase tracking-wider">
          <span className="flex items-center gap-2">
            <Server size={16} className="text-primary" /> System Status Monitor
          </span>
          <span className="text-[10px] font-mono text-muted">Last synchronized: 2 minutes ago</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { name: "GIS Data Service", status: "Operational" },
            { name: "Risk Prediction", status: "Operational" },
            { name: "Alert Service", status: "Operational" },
            { name: "Map Service", status: "Operational" },
          ].map((s) => (
            <div key={s.name} className="p-3.5 bg-muted-bg/40 rounded-xl border border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="size-2 rounded-full bg-risk-low animate-pulse"></span>
                <span className="text-xs font-bold text-foreground">{s.name}</span>
              </div>
              <span className="text-[10px] font-bold text-risk-low uppercase tracking-wider">{s.status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Requirement #14: Reset Confirmation Dialog Modal */}
      <AnimatePresence>
        {showResetModal && (
          <div className="fixed inset-0 bg-background/60 backdrop-blur-xs z-[999] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.94 }}
              className="bg-card border border-border rounded-2xl shadow-2xl p-6 max-w-sm w-full space-y-4"
            >
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-full bg-risk-very-high/10 text-risk-very-high flex items-center justify-center shrink-0">
                  <AlertTriangle size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-base text-foreground">Reset Settings?</h3>
                  <p className="text-xs text-muted mt-0.5">
                    This will restore all LANDGUARD AI preferences to their default values.
                  </p>
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => setShowResetModal(false)}
                  className="flex-1 py-2.5 px-4 text-xs font-bold rounded-xl border border-border bg-card hover:bg-muted-bg transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmReset}
                  className="flex-1 py-2.5 px-4 text-xs font-bold rounded-xl bg-risk-very-high text-white hover:bg-risk-very-high/90 transition shadow-md"
                >
                  Reset Defaults
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
