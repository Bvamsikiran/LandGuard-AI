import React, { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Globe, ChevronDown, Bell, User, Check } from "lucide-react"
import { REGIONS, USER_PROFILE } from "../../data/northeast_dataset"
import { Alert } from "../../types"
import NotificationsPopover from "../common/NotificationsPopover"
import ProfilePopover from "../common/ProfilePopover"

export default function Header({
  selectedRegion,
  setSelectedRegion,
  alerts,
  onNavigateToMapLocation,
  onNavigateSettings,
  addToast,
}: {
  selectedRegion: string
  setSelectedRegion: (r: string) => void
  alerts: Alert[]
  onNavigateToMapLocation: (locId: number) => void
  onNavigateSettings: () => void
  addToast: (msg: string, type?: "success" | "error") => void
}) {
  const [showRegionDropdown, setShowRegionDropdown] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)

  const regionRef = useRef<HTMLDivElement>(null)
  const activeAlertsCount = alerts.filter((a) => a.status === "Active").length

  // Click outside & ESC for Region dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (regionRef.current && !regionRef.current.contains(e.target as Node)) {
        setShowRegionDropdown(false)
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowRegionDropdown(false)
    }
    document.addEventListener("mousedown", handleClickOutside)
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [])

  return (
    <header className="h-14 bg-card border-b border-border flex items-center justify-between px-5 shrink-0 z-30 shadow-xs relative">
      <div className="flex items-center gap-3">
        {/* Real Floating Region Dropdown */}
        <div className="relative" ref={regionRef}>
          <button
            onClick={() => {
              setShowRegionDropdown(!showRegionDropdown)
              setShowNotifications(false)
              setShowProfileMenu(false)
            }}
            className={`flex items-center gap-2 text-xs sm:text-sm font-bold px-3 py-1.5 rounded-xl border transition-all shadow-xs ${
              showRegionDropdown
                ? "bg-primary text-white border-primary"
                : "bg-muted-bg/80 border-border text-foreground hover:bg-muted-bg"
            }`}
          >
            <Globe size={14} className={showRegionDropdown ? "text-white" : "text-primary"} />
            <span>REGION: {selectedRegion}</span>
            <ChevronDown size={12} className={`transition-transform ${showRegionDropdown ? "rotate-180" : ""}`} />
          </button>

          <AnimatePresence>
            {showRegionDropdown && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.96 }}
                transition={{ duration: 0.15, ease: "easeOut" }}
                className="absolute left-0 top-full mt-2 w-56 bg-card/96 backdrop-blur-md border border-border rounded-2xl shadow-2xl z-[600] overflow-hidden p-2"
              >
                <div className="px-3 py-1.5 border-b border-border mb-1">
                  <span className="text-[10px] font-extrabold uppercase text-muted tracking-wider">
                    Select Region
                  </span>
                </div>
                <div className="max-h-64 overflow-y-auto space-y-0.5">
                  {REGIONS.map((r) => {
                    const isSelected = r === selectedRegion
                    return (
                      <button
                        key={r}
                        onClick={() => {
                          setSelectedRegion(r)
                          setShowRegionDropdown(false)
                          addToast(`Region view updated to ${r}`)
                        }}
                        className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold flex items-center justify-between transition-colors ${
                          isSelected
                            ? "bg-primary/10 text-primary font-bold"
                            : "text-foreground hover:bg-muted-bg"
                        }`}
                      >
                        <span>{r}</span>
                        {isSelected && <Check size={14} className="text-primary" />}
                      </button>
                    )
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="hidden md:block h-4 w-px bg-border"></div>
        <span className="hidden lg:block text-xs text-muted font-medium">
          AI-Powered Landslide Risk Prediction & Early Warning
        </span>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* Live Data Badge */}
        <div className="flex items-center gap-2 bg-risk-low/10 border border-risk-low/20 px-2.5 sm:px-3 py-1.5 rounded-full">
          <span className="size-2 rounded-full bg-risk-low animate-pulse"></span>
          <span className="text-[10px] sm:text-xs font-bold text-risk-low tracking-wide">LIVE GIS DATA</span>
          <span className="text-[10px] text-muted hidden lg:block">· Updated 2 mins ago</span>
        </div>

        {/* Notifications Bell */}
        <div className="relative">
          <button
            onClick={() => {
              setShowNotifications(!showNotifications)
              setShowRegionDropdown(false)
              setShowProfileMenu(false)
            }}
            className={`relative text-muted hover:text-foreground transition-colors p-2 rounded-xl hover:bg-muted-bg border ${
              showNotifications ? "bg-muted-bg border-border text-foreground" : "border-transparent"
            }`}
            title="Notifications"
          >
            <Bell size={18} />
            {activeAlertsCount > 0 && (
              <span className="absolute top-1 right-1 size-4 rounded-full bg-risk-very-high text-[9px] text-white flex items-center justify-center font-bold border border-card shadow-xs">
                {activeAlertsCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <NotificationsPopover
              alerts={alerts}
              onClose={() => setShowNotifications(false)}
              onSelectAlert={onNavigateToMapLocation}
            />
          )}
        </div>

        {/* Profile Trigger - CHEVRON REMOVED, Clickable Trigger */}
        <div className="relative">
          <button
            onClick={() => {
              setShowProfileMenu(!showProfileMenu)
              setShowRegionDropdown(false)
              setShowNotifications(false)
            }}
            className="flex items-center gap-2.5 p-1 sm:px-2 sm:py-1 rounded-xl hover:bg-muted-bg transition-colors group cursor-pointer border border-transparent hover:border-border"
            title="User Profile"
          >
            <div className="size-8 rounded-full bg-slate-700 border border-primary/40 flex items-center justify-center text-white font-semibold text-xs shadow-xs">
              <User size={15} />
            </div>
            <div className="hidden md:block text-left">
              <div className="text-xs font-bold text-foreground leading-none group-hover:text-primary transition-colors">
                {USER_PROFILE.name}
              </div>
              <div className="text-[9px] text-muted font-medium mt-0.5">{USER_PROFILE.role}</div>
            </div>
          </button>

          {showProfileMenu && (
            <ProfilePopover
              onClose={() => setShowProfileMenu(false)}
              onNavigateSettings={onNavigateSettings}
              addToast={addToast}
            />
          )}
        </div>
      </div>
    </header>
  )
}
