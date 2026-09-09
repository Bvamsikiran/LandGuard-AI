import React from "react"
import { motion } from "framer-motion"
import {
  LayoutDashboard,
  Map,
  Bell,
  MapPin,
  History,
  Flag,
  BarChart2,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  User,
  ShieldCheck,
} from "lucide-react"
import { View } from "../../types"

export default function Sidebar({
  currentView,
  setCurrentView,
  collapsed,
  setCollapsed,
  activeAlertsCount,
}: {
  currentView: View
  setCurrentView: (view: View) => void
  collapsed: boolean
  setCollapsed: (c: boolean) => void
  activeAlertsCount: number
}) {
  return (
    <motion.div
      animate={{ width: collapsed ? 64 : 256 }}
      transition={{ duration: 0.22, ease: "easeInOut" }}
      className="bg-sidebar text-sidebar-foreground flex flex-col shrink-0 border-r border-sidebar-hover overflow-hidden relative z-20"
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-sidebar-hover shrink-0 justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className="size-8 rounded-xl bg-risk-high flex items-center justify-center shrink-0 shadow-md shadow-risk-high/30">
            <MapPin className="text-white" size={16} />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="font-bold text-sm tracking-wide text-white truncate">LANDGUARD AI</h1>
              <p className="text-[9px] text-slate-400 uppercase tracking-widest">Northeast India GIS</p>
            </div>
          )}
        </div>
        {!collapsed && (
          <button
            onClick={() => setCollapsed(true)}
            className="text-slate-500 hover:text-white p-1 rounded-lg transition-colors shrink-0"
            title="Collapse sidebar"
          >
            <ChevronLeft size={16} />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 flex flex-col gap-0.5">
        <NavItem
          icon={<LayoutDashboard size={17} />}
          label="Dashboard"
          active={currentView === "dashboard"}
          collapsed={collapsed}
          onClick={() => setCurrentView("dashboard")}
        />
        <NavItem
          icon={<Map size={17} />}
          label="Risk Map"
          active={currentView === "map"}
          collapsed={collapsed}
          onClick={() => setCurrentView("map")}
        />
        <NavItem
          icon={<Bell size={17} />}
          label="Alerts"
          active={currentView === "alerts"}
          collapsed={collapsed}
          onClick={() => setCurrentView("alerts")}
          badge={activeAlertsCount}
        />
        <NavItem
          icon={<MapPin size={17} />}
          label="Location Analysis"
          active={currentView === "analysis"}
          collapsed={collapsed}
          onClick={() => setCurrentView("analysis")}
        />
        <NavItem
          icon={<History size={17} />}
          label="Historical Landslides"
          active={currentView === "historical"}
          collapsed={collapsed}
          onClick={() => setCurrentView("historical")}
        />
        <NavItem
          icon={<Flag size={17} />}
          label="Field Reports"
          active={currentView === "reports"}
          collapsed={collapsed}
          onClick={() => setCurrentView("reports")}
        />

        {collapsed ? (
          <div className="my-3 mx-2 h-px bg-sidebar-hover"></div>
        ) : (
          <div className="mt-4 mb-2 px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
            AI & System
          </div>
        )}

        <NavItem
          icon={<BarChart2 size={17} />}
          label="Model Insights"
          active={currentView === "insights"}
          collapsed={collapsed}
          onClick={() => setCurrentView("insights")}
        />
        <NavItem
          icon={<Activity size={17} />}
          label="Model Status"
          active={currentView === "status"}
          collapsed={collapsed}
          onClick={() => setCurrentView("status")}
        />
        <NavItem
          icon={<Settings size={17} />}
          label="Settings"
          active={currentView === "settings"}
          collapsed={collapsed}
          onClick={() => setCurrentView("settings")}
        />
      </nav>

      {/* User profile footer */}
      <div className="p-3 border-t border-sidebar-hover shrink-0">
        {collapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            className="w-full flex items-center justify-center p-2 rounded-xl hover:bg-sidebar-hover transition-colors text-slate-400 hover:text-white"
            title="Expand sidebar"
          >
            <ChevronRight size={16} />
          </button>
        ) : (
          <div className="bg-sidebar-hover rounded-xl p-3 flex items-center gap-3">
            <div className="size-8 rounded-full bg-slate-600 flex items-center justify-center shrink-0">
              <User size={14} className="text-slate-300" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-bold text-white truncate">Dr. Ananya Roy</div>
              <div className="text-[10px] text-slate-400 truncate flex items-center gap-1">
                <ShieldCheck size={10} className="text-risk-low" /> GIS Lead Analyst
              </div>
            </div>
            <button
              onClick={() => setCurrentView("settings")}
              className="text-slate-500 hover:text-white p-1 rounded-lg transition-colors shrink-0"
              title="Open Settings"
            >
              <Settings size={14} />
            </button>
          </div>
        )}
      </div>
    </motion.div>
  )
}

function NavItem({
  icon,
  label,
  active,
  badge,
  onClick,
  collapsed,
}: {
  icon: React.ReactNode
  label: string
  active?: boolean
  badge?: number
  onClick?: () => void
  collapsed?: boolean
}) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? label : undefined}
      className={`w-full flex items-center gap-3 rounded-xl text-xs font-semibold transition-all text-left relative
        ${collapsed ? "justify-center px-2 py-3" : "px-3.5 py-2.5"}
        ${
          active
            ? "bg-primary/20 text-white font-bold shadow-xs"
            : "text-slate-400 hover:bg-sidebar-hover hover:text-white"
        }`}
    >
      {active && <span className="absolute left-0 top-2 bottom-2 w-1 bg-primary rounded-r-full"></span>}
      <span className={`shrink-0 ${active ? "text-primary" : ""}`}>{icon}</span>
      {!collapsed && <span className="flex-1 truncate">{label}</span>}
      {!collapsed && badge !== undefined && badge > 0 && (
        <span className="bg-risk-very-high text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
          {badge}
        </span>
      )}
      {collapsed && badge !== undefined && badge > 0 && (
        <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-risk-very-high"></span>
      )}
    </button>
  )
}
