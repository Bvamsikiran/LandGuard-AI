import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2, AlertTriangle } from "lucide-react"

import {
  View,
  LocationData,
  Alert,
  HistoricalEvent,
  FieldReport,
  AppSettings,
  ThemeMode,
} from "./types"
import {
  DEFAULT_SETTINGS,
  DEFAULT_REGION,
} from "./data/central_store"
import {
  riskPredictionService,
  alertsService,
  historicalLandslideService,
  reportService,
} from "./services/riskService"

import Header from "./components/layout/Header"
import Sidebar from "./components/layout/Sidebar"

import DashboardView from "./views/DashboardView"
import MapView from "./views/MapView"
import AlertsView from "./views/AlertsView"
import LocationAnalysisView from "./views/LocationAnalysisView"
import HistoricalLandslidesView from "./views/HistoricalLandslidesView"
import FieldReportsView from "./views/FieldReportsView"
import ModelInsightsView from "./views/ModelInsightsView"
import ModelStatusView from "./views/ModelStatusView"
import SettingsView from "./views/SettingsView"

export default function App() {
  const [currentView, setCurrentView] = useState<View>("map")
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null)
  const [selectedRegion, setSelectedRegion] = useState<string>(DEFAULT_REGION)
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false)

  // Service Layer Data States
  const [locations, setLocations] = useState<LocationData[]>([])
  const [historicalEvents, setHistoricalEvents] = useState<HistoricalEvent[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [reports, setReports] = useState<FieldReport[]>([])

  // Load Data via Service Layer (synchronized with selected region)
  useEffect(() => {
    riskPredictionService.getLocations(selectedRegion).then(setLocations)
    historicalLandslideService.getHistoricalEvents(selectedRegion).then(setHistoricalEvents)
    alertsService.getAlerts(selectedRegion).then(setAlerts)
    reportService.getReports().then(setReports)
  }, [selectedRegion])


  // Settings & Theme Initialization
  const [settings, setSettings] = useState<AppSettings>(() => {
    const saved = localStorage.getItem("landguard_settings")
    if (saved) {
      try {
        return JSON.parse(saved)
      } catch (e) {
        // fallback
      }
    }
    return DEFAULT_SETTINGS
  })

  // Synchronize theme with DOM root class & localStorage
  useEffect(() => {
    localStorage.setItem("landguard_settings", JSON.stringify(settings))
    const themeMode: ThemeMode = settings.appearance.theme

    const root = document.documentElement
    root.classList.remove("light", "dark")

    if (themeMode === "system") {
      const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches
      root.classList.add(systemDark ? "dark" : "light")
    } else {
      root.classList.add(themeMode)
    }
  }, [settings])

  const [toasts, setToasts] = useState<
    Array<{ id: number; message: string; type: "success" | "error" }>
  >([])

  const addToast = (message: string, type: "success" | "error" = "success") => {
    const id = Date.now()
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500)
  }

  const handleAcknowledgeAlert = async (id: number) => {
    const updated = await alertsService.acknowledgeAlert(id, alerts)
    setAlerts(updated)
    addToast("✓ Alert acknowledged successfully")
  }

  const handleNavigateToMapLocation = (locationId?: number) => {
    setCurrentView("map")
    if (locationId !== undefined) {
      setSelectedLocationId(locationId)
    }
  }

  const handleAddReport = async (newReport: FieldReport) => {
    const updated = await reportService.submitReport(newReport, reports)
    setReports(updated)
  }

  const activeAlertsCount = alerts.filter((a) => a.status === "Active").length

  return (
    <div className="flex h-screen w-full bg-background font-sans text-foreground overflow-hidden">
      {/* Toast Notifications */}
      <div className="fixed bottom-4 right-4 z-[999] flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 16, scale: 0.92 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.92 }}
              className={`px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-xs font-bold border min-w-[240px] ${
                toast.type === "success"
                  ? "bg-card text-foreground border-border border-l-4 border-l-risk-low"
                  : "bg-risk-very-high-bg text-risk-very-high border-risk-very-high/30"
              }`}
            >
              {toast.type === "success" ? (
                <CheckCircle2 size={16} className="text-risk-low shrink-0" />
              ) : (
                <AlertTriangle size={16} className="shrink-0" />
              )}
              {toast.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Navigation Sidebar */}
      <Sidebar
        currentView={currentView}
        setCurrentView={(view) => {
          setCurrentView(view)
          if (view !== "map") {
            setSelectedLocationId(null)
          }
        }}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        activeAlertsCount={activeAlertsCount}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        <Header
          selectedRegion={selectedRegion}
          setSelectedRegion={(r) => {
            setSelectedRegion(r)
            if (currentView !== "map") {
              setCurrentView("map")
            }
          }}
          alerts={alerts}
          onNavigateToMapLocation={handleNavigateToMapLocation}
          onNavigateSettings={() => setCurrentView("settings")}
          addToast={addToast}
        />

        <main className="flex-1 overflow-y-auto overflow-x-hidden relative">
          {currentView === "dashboard" && (
            <DashboardView
              locations={locations}
              alerts={alerts}
              selectedRegion={selectedRegion}
              onNavigateToMap={handleNavigateToMapLocation}
            />
          )}

          {currentView === "map" && (
            <MapView
              locations={locations}
              historicalEvents={historicalEvents}
              selectedLocationId={selectedLocationId}
              selectedRegion={selectedRegion}
              setSelectedLocationId={setSelectedLocationId}
              addToast={addToast}
            />
          )}

          {currentView === "alerts" && (
            <AlertsView
              alerts={alerts}
              selectedRegion={selectedRegion}
              onViewDetails={handleNavigateToMapLocation}
              onAcknowledge={handleAcknowledgeAlert}
            />
          )}

          {currentView === "analysis" && (
            <LocationAnalysisView
              locations={locations}
              selectedRegion={selectedRegion}
              onNavigateToMap={handleNavigateToMapLocation}
            />
          )}

          {currentView === "historical" && (
            <HistoricalLandslidesView
              events={historicalEvents}
              selectedRegion={selectedRegion}
              onNavigateToMap={() => setCurrentView("map")}
            />
          )}

          {currentView === "reports" && (
            <FieldReportsView
              reports={reports}
              onAddReport={handleAddReport}
              addToast={addToast}
            />
          )}

          {currentView === "insights" && <ModelInsightsView />}

          {currentView === "status" && <ModelStatusView />}

          {currentView === "settings" && (
            <SettingsView
              settings={settings}
              onSaveSettings={(newSet) => setSettings(newSet)}
              addToast={addToast}
            />
          )}
        </main>
      </div>
    </div>
  )
}
