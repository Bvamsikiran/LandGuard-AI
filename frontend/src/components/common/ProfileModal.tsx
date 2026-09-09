import React from "react"
import { motion } from "framer-motion"
import { User, Shield, Mail, Building, Settings, LogOut, X, CheckCircle2 } from "lucide-react"
import { UserProfile } from "../../types"

export default function ProfileModal({
  profile,
  onClose,
  onNavigateSettings,
  addToast,
}: {
  profile: UserProfile
  onClose: () => void
  onNavigateSettings: () => void
  addToast: (msg: string, type?: "success" | "error") => void
}) {
  return (
    <div className="fixed inset-0 bg-background/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.94 }}
        className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md overflow-hidden relative"
      >
        <div className="bg-sidebar p-6 text-sidebar-foreground relative border-b border-sidebar-hover">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X size={16} />
          </button>
          <div className="flex items-center gap-4">
            <div className="size-16 rounded-full bg-slate-700 border-2 border-primary flex items-center justify-center text-primary text-xl font-bold">
              <User size={28} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">{profile.name}</h2>
              <p className="text-xs text-primary font-medium mt-0.5">{profile.role}</p>
              <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-slate-300">
                <Shield size={11} className="text-risk-low" /> Authorized Analyst — Level 4 GIS Access
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 bg-muted-bg rounded-xl border border-border">
              <Mail size={16} className="text-muted shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-[10px] text-muted font-bold uppercase tracking-wider">Email Address</div>
                <div className="text-xs font-semibold text-foreground truncate">{profile.email}</div>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 bg-muted-bg rounded-xl border border-border">
              <Building size={16} className="text-muted shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-[10px] text-muted font-bold uppercase tracking-wider">Organization</div>
                <div className="text-xs font-semibold text-foreground truncate">{profile.organization}</div>
              </div>
            </div>
          </div>

          <div className="p-4 bg-primary/5 rounded-xl border border-primary/20 space-y-2">
            <div className="text-xs font-bold text-primary flex items-center gap-1.5">
              <CheckCircle2 size={14} /> Active Session Status
            </div>
            <p className="text-xs text-muted leading-relaxed">
              Connected to Northeastern India Real-Time GIS Predictive Pipeline & Alert Broadcast Network.
            </p>
          </div>

          <div className="pt-2 flex gap-2">
            <button
              onClick={() => {
                onClose()
                onNavigateSettings()
              }}
              className="flex-1 py-2.5 px-4 text-xs font-bold rounded-xl border border-border bg-card hover:bg-muted-bg transition flex items-center justify-center gap-2"
            >
              <Settings size={14} /> Settings
            </button>
            <button
              onClick={() => {
                addToast("User session reset for demo mode")
                onClose()
              }}
              className="flex-1 py-2.5 px-4 text-xs font-bold rounded-xl bg-risk-very-high/10 text-risk-very-high hover:bg-risk-very-high/20 transition flex items-center justify-center gap-2"
            >
              <LogOut size={14} /> Sign Out Demo
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
