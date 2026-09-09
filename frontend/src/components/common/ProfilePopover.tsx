import React, { useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { User, Settings, Bell, HelpCircle, LogOut, Shield } from "lucide-react"
import { USER_PROFILE } from "../../data/northeast_dataset"

export default function ProfilePopover({
  onClose,
  onNavigateSettings,
  addToast,
}: {
  onClose: () => void
  onNavigateSettings: () => void
  addToast: (msg: string, type?: "success" | "error") => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    document.addEventListener("mousedown", handleClickOutside)
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [onClose])

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0, y: 8, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.96 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      className="absolute right-4 top-14 w-72 bg-card/95 backdrop-blur-md border border-border rounded-2xl shadow-2xl z-[600] overflow-hidden"
    >
      {/* Profile Header */}
      <div className="p-4 border-b border-border bg-muted-bg/40">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-full bg-slate-700 border-2 border-primary flex items-center justify-center text-white shrink-0">
            <User size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="font-bold text-sm text-foreground truncate">{USER_PROFILE.name}</h3>
            <p className="text-xs text-primary font-medium truncate">{USER_PROFILE.role}</p>
            <div className="text-[10px] text-muted flex items-center gap-1 mt-0.5">
              <Shield size={10} className="text-risk-low" /> Authorized Level 4 GIS Access
            </div>
          </div>
        </div>
      </div>

      {/* Menu Options */}
      <div className="p-1.5 space-y-0.5">
        <button
          onClick={() => {
            onClose()
            onNavigateSettings()
          }}
          className="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-foreground hover:bg-muted-bg flex items-center gap-2.5 transition-colors"
        >
          <User size={15} className="text-muted" /> View Profile & Credentials
        </button>

        <button
          onClick={() => {
            onClose()
            onNavigateSettings()
          }}
          className="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-foreground hover:bg-muted-bg flex items-center gap-2.5 transition-colors"
        >
          <Settings size={15} className="text-muted" /> Account Settings
        </button>

        <button
          onClick={() => {
            onClose()
            onNavigateSettings()
          }}
          className="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-foreground hover:bg-muted-bg flex items-center gap-2.5 transition-colors"
        >
          <Bell size={15} className="text-muted" /> Notification Preferences
        </button>

        <button
          onClick={() => {
            onClose()
            addToast("Help & Support documentation center opened")
          }}
          className="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-foreground hover:bg-muted-bg flex items-center gap-2.5 transition-colors"
        >
          <HelpCircle size={15} className="text-muted" /> Help & Support
        </button>

        <div className="h-px bg-border my-1"></div>

        <button
          onClick={() => {
            onClose()
            addToast("User session reset for demo presentation mode")
          }}
          className="w-full text-left px-3 py-2 rounded-xl text-xs font-bold text-risk-very-high hover:bg-risk-very-high/10 flex items-center gap-2.5 transition-colors"
        >
          <LogOut size={15} /> Sign Out Demo Session
        </button>
      </div>
    </motion.div>
  )
}
