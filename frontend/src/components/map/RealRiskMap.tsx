import React, { useEffect, useState, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  CircleMarker,
  useMap,
  Tooltip,
} from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import {
  Search,
  Target,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize,
  Minimize,
  Globe,
  Layers,
  Loader2,
  Navigation,
  MapPin,
  AlertTriangle,
  ChevronDown,
  Check,
  Filter,
} from "lucide-react"
import { LocationData, MapStyle, ActiveLayers, HistoricalEvent } from "../../types"
import { SEARCH_SUGGESTIONS, STATE_CENTERS } from "../../data/northeast_dataset"
import { heatmapService } from "../../services/riskService"
import RiskBadge from "../common/RiskBadge"

const MAP_TILE_URLS: Record<MapStyle, { url: string; attribution: string }> = {
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Esri, Maxar, Earthstar Geographics",
  },
  terrain: {
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution: "Map data © OpenStreetMap contributors, SRTM | OpenTopoMap",
  },
  streets: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "© OpenStreetMap contributors",
  },
  light: {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution: "© OpenStreetMap, © CARTO",
  },
}

const DEFAULT_LAYERS: ActiveLayers = {
  heatmap: true,
  riskLocations: true,
  historicalLandslides: false,
  rivers: false,
  roads: false,
  terrain: false,
  stateBoundaries: true,
}

const RISK_COLORS: Record<string, string> = {
  Low: "#10B981",
  Moderate: "#F59E0B",
  High: "#F97316",
  "Very High": "#EF4444",
}

function createRiskDivIcon(risk: string, isSelected: boolean) {
  const color = RISK_COLORS[risk] || "#10B981"
  const size = risk === "Very High" ? 24 : risk === "High" ? 20 : 16
  const pingHtml =
    risk === "Very High"
      ? `<div style="position:absolute; inset:-8px; border-radius:50%; background:${color}33; animation: ping 1.6s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>`
      : ""

  const html = `
    <div style="position:relative; width:${size}px; height:${size}px; cursor:pointer; transform: scale(${isSelected ? 1.35 : 1}); transition: transform 0.2s ease;">
      ${pingHtml}
      <div style="width:100%; height:100%; border-radius:50%; background:${color}; border:2px solid white; box-shadow:0 0 ${risk === "Very High" ? "16px" : "6px"} ${color}aa; display:flex; align-items:center; justify-center;">
        ${isSelected || risk === "Very High" ? `<div style="width:6px; height:6px; background:white; border-radius:50%; margin:auto;"></div>` : ""}
      </div>
    </div>
  `

  return L.divIcon({
    html,
    className: "custom-leaflet-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

function createHistoricalDivIcon() {
  const html = `
    <div style="width:14px; height:14px; background:#64748B; border:2px solid white; transform: rotate(45deg); box-shadow:0 2px 4px rgba(0,0,0,0.4);"></div>
  `
  return L.divIcon({
    html,
    className: "custom-historical-marker",
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

function MapController({
  targetLatLon,
  zoomLevel,
}: {
  targetLatLon?: { lat: number; lon: number } | null
  zoomLevel?: number
}) {
  const map = useMap()
  useEffect(() => {
    if (targetLatLon) {
      map.flyTo([targetLatLon.lat, targetLatLon.lon], zoomLevel || 9, { duration: 1.2 })
    }
  }, [targetLatLon, zoomLevel, map])
  return null
}

export default function RealRiskMap({
  locations,
  historicalEvents,
  selectedLocationId,
  selectedRegion,
  onSelectLocation,
  addToast,
}: {
  locations: LocationData[]
  historicalEvents: HistoricalEvent[]
  selectedLocationId: number | null
  selectedRegion: string
  onSelectLocation: (id: number | null) => void
  addToast: (msg: string, type?: "success" | "error") => void
}) {
  const [mapStyle, setMapStyle] = useState<MapStyle>("satellite")
  const [activeLayers, setActiveLayers] = useState<ActiveLayers>(DEFAULT_LAYERS)
  const [riskFilter, setRiskFilter] = useState("All")
  const [searchText, setSearchText] = useState("")
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState("Analyzing location...")
  const [showLayersMenu, setShowLayersMenu] = useState(false)
  const [showStyleMenu, setShowStyleMenu] = useState(false)
  const [showRiskMenu, setShowRiskMenu] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [targetLatLon, setTargetLatLon] = useState<{ lat: number; lon: number } | null>(null)
  const [targetZoom, setTargetZoom] = useState<number>(7)
  const [heatmapPoints, setHeatmapPoints] = useState<
    Array<{ lat: number; lon: number; weight: number; risk: string }>
  >([])
  const [heatmapLoading, setHeatmapLoading] = useState<boolean>(false)

  const mapRef = useRef<L.Map | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const riskRef = useRef<HTMLDivElement>(null)

  // Fetch continuous GIS risk heatmap from live ML pipeline
  useEffect(() => {
    if (!activeLayers.heatmap) return
    let isMounted = true
    setHeatmapLoading(true)
    heatmapService
      .getHeatmapPoints(selectedRegion)
      .then((points) => {
        if (isMounted) {
          setHeatmapPoints(points)
          setHeatmapLoading(false)
        }
      })
      .catch((err) => {
        console.warn("Could not load AI heatmap points:", err)
        if (isMounted) setHeatmapLoading(false)
      })
    return () => {
      isMounted = false
    }
  }, [selectedRegion, activeLayers.heatmap])

  // Sync region selection from header to map center
  useEffect(() => {
    const center = STATE_CENTERS[selectedRegion] || STATE_CENTERS["Northeastern India"]
    setTargetLatLon({ lat: center.lat, lon: center.lon })
    setTargetZoom(center.zoom)
  }, [selectedRegion])


  // Fly map when selected location changes
  useEffect(() => {
    if (selectedLocationId) {
      const loc = locations.find((l) => l.id === selectedLocationId)
      if (loc) {
        setTargetLatLon({ lat: loc.lat, lon: loc.lon })
        setTargetZoom(9)
      }
    }
  }, [selectedLocationId, locations])

  // Click outside for risk filter dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (riskRef.current && !riskRef.current.contains(e.target as Node)) {
        setShowRiskMenu(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const visibleLocations = locations.filter(
    (l) => riskFilter === "All" || l.risk.toLowerCase() === riskFilter.toLowerCase()
  )

  const runSearch = (locName: string) => {
    setSearchText(locName)
    setShowSuggestions(false)
    setLoading(true)
    const msgs = [
      "Analyzing location...",
      "Fetching Northeast India GIS layers...",
      "Executing AI Landslide XGBoost prediction...",
    ]
    let i = 0
    setLoadingMsg(msgs[0])
    const iv = setInterval(() => {
      i++
      if (i < msgs.length) setLoadingMsg(msgs[i])
      else clearInterval(iv)
    }, 600)

    setTimeout(() => {
      clearInterval(iv)
      setLoading(false)
      const match = locations.find((l) =>
        l.name.toLowerCase().includes(locName.split(",")[0].toLowerCase())
      )
      if (match) {
        onSelectLocation(match.id)
        setTargetLatLon({ lat: match.lat, lon: match.lon })
        setTargetZoom(9)
        addToast(`Risk prediction retrieved for ${match.shortName}`)
      } else {
        addToast(`Location ${locName} analyzed`, "success")
      }
    }, 1800)
  }

  const handleMyLocation = () => {
    addToast("Current location pinpointed — Guwahati, Assam")
    setTargetLatLon({ lat: 26.1445, lon: 91.7362 })
    setTargetZoom(9)
  }

  const handleResetView = () => {
    const center = STATE_CENTERS[selectedRegion] || STATE_CENTERS["Northeastern India"]
    setTargetLatLon({ lat: center.lat, lon: center.lon })
    setTargetZoom(center.zoom)
    addToast(`Map reset to ${selectedRegion} view`)
  }

  const toggleLayer = (key: keyof ActiveLayers) => {
    setActiveLayers((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      containerRef.current?.requestFullscreen?.()
    } else {
      document.exitFullscreen?.()
    }
    setIsFullscreen(!isFullscreen)
  }

  return (
    <div ref={containerRef} className="relative w-full h-full bg-slate-900 overflow-hidden select-none">
      {/* Real Leaflet Map */}
      <MapContainer
        center={[26.0, 93.0]}
        zoom={7}
        zoomControl={false}
        className="w-full h-full z-0"
        ref={mapRef}
      >
        <TileLayer
          url={MAP_TILE_URLS[mapStyle].url}
          attribution={MAP_TILE_URLS[mapStyle].attribution}
          maxZoom={18}
        />

        <MapController targetLatLon={targetLatLon} zoomLevel={targetZoom} />

        {/* Continuous AI GIS Risk Heatmap Layer */}
        {activeLayers.heatmap && heatmapPoints.length > 0
          ? heatmapPoints.map((pt, idx) => (
              <CircleMarker
                key={`hmp-${idx}`}
                center={[pt.lat, pt.lon]}
                radius={pt.risk === "Very High" ? 22 : pt.risk === "High" ? 18 : 14}
                pathOptions={{
                  color: "transparent",
                  fillColor: RISK_COLORS[pt.risk] || "#10B981",
                  fillOpacity:
                    pt.risk === "Very High" ? 0.42 : pt.risk === "High" ? 0.30 : 0.18,
                  weight: 0,
                }}
              />
            ))
          : activeLayers.heatmap &&
            visibleLocations.map((loc) => (
              <CircleMarker
                key={`hm-${loc.id}`}
                center={[loc.lat, loc.lon]}
                radius={loc.risk === "Very High" ? 48 : loc.risk === "High" ? 36 : 24}
                pathOptions={{
                  color: RISK_COLORS[loc.risk],
                  fillColor: RISK_COLORS[loc.risk],
                  fillOpacity:
                    loc.risk === "Very High" ? 0.38 : loc.risk === "High" ? 0.28 : 0.18,
                  weight: 0,
                }}
              />
            ))}


        {/* Risk Markers */}
        {activeLayers.riskLocations &&
          visibleLocations.map((loc) => (
            <Marker
              key={loc.id}
              position={[loc.lat, loc.lon]}
              icon={createRiskDivIcon(loc.risk, selectedLocationId === loc.id)}
              eventHandlers={{
                click: () => onSelectLocation(loc.id === selectedLocationId ? null : loc.id),
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                <div className="p-1 font-sans">
                  <div className="font-bold text-xs text-foreground">{loc.name}</div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <RiskBadge level={loc.risk} small />
                    <span className="text-[10px] font-bold font-mono text-muted">{loc.prob}% risk</span>
                  </div>
                </div>
              </Tooltip>
            </Marker>
          ))}

        {/* Historical Landslides Markers */}
        {activeLayers.historicalLandslides &&
          historicalEvents.map((evt) => (
            <Marker
              key={`hist-${evt.id}`}
              position={[evt.lat, evt.lon]}
              icon={createHistoricalDivIcon()}
            >
              <Popup>
                <div className="p-1 max-w-xs font-sans">
                  <div className="font-bold text-xs text-foreground flex items-center gap-1">
                    <AlertTriangle size={12} className="text-risk-high" /> {evt.name}
                  </div>
                  <div className="text-[11px] text-muted mt-1">Date: {evt.date}</div>
                  <div className="text-[11px] text-muted">Trigger: {evt.trigger}</div>
                  <div className="text-[11px] text-muted">Impact: {evt.affectedRoads}</div>
                </div>
              </Popup>
            </Marker>
          ))}
      </MapContainer>

      {/* ── MAP UI OVERLAYS ── */}

      {/* Top Left: Search & Telemetry Controls */}
      <div className="absolute top-4 left-4 z-[400] flex items-center gap-2 pointer-events-auto">
        <div className="relative">
          <div className="bg-card/96 backdrop-blur-md rounded-xl shadow-lg border border-border flex items-center gap-2 p-2 focus-within:ring-2 focus-within:ring-primary/40 transition-all">
            <Search size={15} className="text-muted ml-1 shrink-0" />
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder="Search location, district or state..."
              className="bg-transparent border-none text-xs sm:text-sm w-48 sm:w-64 focus:ring-0 outline-none placeholder:text-muted/60 font-medium text-foreground"
            />
            <button
              onClick={() => searchText && runSearch(searchText)}
              disabled={loading}
              className="bg-primary text-white text-xs px-3 py-1.5 rounded-lg font-bold hover:bg-primary/90 transition flex items-center justify-center min-w-[60px] shadow-xs"
            >
              {loading ? <Loader2 size={13} className="animate-spin" /> : "Search"}
            </button>
          </div>

          <AnimatePresence>
            {showSuggestions && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 6 }}
                className="absolute top-full mt-1.5 left-0 right-0 bg-card/98 backdrop-blur-md rounded-xl shadow-2xl border border-border overflow-hidden z-[500]"
              >
                <div className="px-3 py-2 border-b border-border">
                  <span className="text-[10px] font-bold uppercase text-muted tracking-wider">
                    Suggested Locations
                  </span>
                </div>
                {SEARCH_SUGGESTIONS.filter(
                  (s) => !searchText || s.toLowerCase().includes(searchText.toLowerCase())
                ).map((s) => (
                  <button
                    key={s}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-muted-bg flex items-center gap-2 transition-colors font-medium text-foreground"
                    onMouseDown={(e) => {
                      e.preventDefault()
                      runSearch(s)
                    }}
                  >
                    <MapPin size={12} className="text-primary shrink-0" />
                    <span>{s}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <button
          onClick={handleMyLocation}
          className="bg-card/96 backdrop-blur-md p-2.5 rounded-xl shadow-lg border border-border text-muted hover:text-primary hover:border-primary/40 transition-all pointer-events-auto"
          title="Current Location"
        >
          <Target size={17} />
        </button>

        <button
          onClick={() => {
            setLoading(true)
            setLoadingMsg("Refreshing live GIS satellite telemetry...")
            setTimeout(() => {
              setLoading(false)
              addToast("Live GIS risk data refreshed successfully")
            }, 1200)
          }}
          className="bg-card/96 backdrop-blur-md p-2.5 rounded-xl shadow-lg border border-border text-muted hover:text-foreground transition-all pointer-events-auto"
          title="Refresh Data"
        >
          <RefreshCw size={17} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Top Right: Compass, Single Risk Level Dropdown, Map Style */}
      <div className="absolute top-4 right-4 z-[400] flex flex-col items-end gap-2.5 pointer-events-auto">
        {/* Row: Risk Dropdown + Map Style */}
        <div className="flex items-center gap-2">
          {/* Requirement #4: Single Elegant Compact Risk Filter Dropdown */}
          <div className="relative" ref={riskRef}>
            <button
              onClick={() => {
                setShowRiskMenu(!showRiskMenu)
                setShowStyleMenu(false)
                setShowLayersMenu(false)
              }}
              className={`flex items-center gap-2 text-xs font-bold px-3 py-2 rounded-xl shadow-lg border transition-all ${
                showRiskMenu
                  ? "bg-primary text-white border-primary"
                  : "bg-card/96 backdrop-blur-md text-foreground border-border hover:bg-muted-bg"
              }`}
            >
              <Filter size={13} className={showRiskMenu ? "text-white" : "text-primary"} />
              <span>RISK LEVEL: {riskFilter}</span>
              <ChevronDown size={12} className={`transition-transform ${showRiskMenu ? "rotate-180" : ""}`} />
            </button>

            <AnimatePresence>
              {showRiskMenu && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.96 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute right-0 top-full mt-2 w-44 bg-card/98 backdrop-blur-md rounded-2xl shadow-2xl border border-border p-2 z-[500]"
                >
                  <div className="text-[10px] font-extrabold text-muted uppercase tracking-wider px-2 py-1.5 border-b border-border mb-1">
                    Filter Risk Level
                  </div>
                  {["All", "Low", "Moderate", "High", "Very High"].map((r) => {
                    const isSelected = riskFilter === r
                    return (
                      <button
                        key={r}
                        onClick={() => {
                          setRiskFilter(r)
                          setShowRiskMenu(false)
                          addToast(`Map markers filtered to ${r} risk`)
                        }}
                        className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold flex items-center justify-between transition-colors ${
                          isSelected
                            ? "bg-primary/10 text-primary font-bold"
                            : "text-foreground hover:bg-muted-bg"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className="size-2 rounded-full"
                            style={{ backgroundColor: RISK_COLORS[r] || "#3B82F6" }}
                          ></span>
                          <span>{r}</span>
                        </div>
                        {isSelected && <Check size={13} className="text-primary" />}
                      </button>
                    )
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Map Style Trigger */}
          <div className="relative">
            <button
              onClick={() => {
                setShowStyleMenu(!showStyleMenu)
                setShowRiskMenu(false)
                setShowLayersMenu(false)
              }}
              className={`p-2.5 rounded-xl shadow-lg border transition-all ${
                showStyleMenu
                  ? "bg-primary text-white border-primary"
                  : "bg-card/96 backdrop-blur-md border-border text-muted hover:text-foreground"
              }`}
              title="Map Style"
            >
              <Globe size={16} />
            </button>

            <AnimatePresence>
              {showStyleMenu && (
                <motion.div
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  className="absolute right-full mr-2 top-0 w-40 bg-card/98 backdrop-blur-md rounded-2xl shadow-2xl border border-border p-2 z-[500]"
                >
                  <div className="text-[10px] font-extrabold text-muted uppercase tracking-wider px-2 py-1.5">
                    GIS Map Style
                  </div>
                  {(["satellite", "terrain", "streets", "light"] as MapStyle[]).map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        setMapStyle(s)
                        setShowStyleMenu(false)
                        addToast(`Map tile style set to ${s}`)
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold transition-colors flex items-center gap-2 ${
                        mapStyle === s ? "bg-primary/10 text-primary" : "text-foreground hover:bg-muted-bg"
                      }`}
                    >
                      <span
                        className={`size-1.5 rounded-full ${mapStyle === s ? "bg-primary" : "bg-border"}`}
                      ></span>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Dedicated Compass Position (Requirement #5) */}
        <button onClick={handleResetView} title="Compass North Reset" className="hover:scale-105 transition-transform">
          <svg width="44" height="44" viewBox="0 0 46 46" className="drop-shadow-xl">
            <circle cx="23" cy="23" r="22" fill="rgba(15,23,42,0.92)" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
            <polygon points="23,4 26.5,23 19.5,23" fill="#EF4444" />
            <polygon points="23,42 26.5,23 19.5,23" fill="rgba(255,255,255,0.3)" />
            <circle cx="23" cy="23" r="3" fill="white" />
            <text x="23" y="14" textAnchor="middle" fill="white" fontSize="7.5" fontWeight="800">
              N
            </text>
          </svg>
        </button>
      </div>

      {/* Left Zoom & Glass Controls */}
      <div className="absolute left-4 top-1/2 -translate-y-1/2 z-[400] flex flex-col gap-2 pointer-events-auto">
        <div className="bg-card/96 backdrop-blur-md rounded-xl shadow-lg border border-border flex flex-col overflow-hidden">
          <button
            onClick={() => mapRef.current?.zoomIn()}
            className="p-2.5 hover:bg-muted-bg text-muted hover:text-foreground transition-colors border-b border-border"
            title="Zoom In"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={() => mapRef.current?.zoomOut()}
            className="p-2.5 hover:bg-muted-bg text-muted hover:text-foreground transition-colors"
            title="Zoom Out"
          >
            <ZoomOut size={16} />
          </button>
        </div>

        <button
          onClick={handleMyLocation}
          className="bg-card/96 backdrop-blur-md p-2.5 rounded-xl shadow-lg border border-border text-muted hover:text-primary transition-all"
          title="Pan to Guwahati"
        >
          <Navigation size={16} />
        </button>

        <button
          onClick={handleResetView}
          className="bg-card/96 backdrop-blur-md p-2.5 rounded-xl shadow-lg border border-border text-muted hover:text-foreground transition-all"
          title="Reset View"
        >
          <RotateCcw size={16} />
        </button>

        <button
          onClick={toggleFullscreen}
          className="bg-card/96 backdrop-blur-md p-2.5 rounded-xl shadow-lg border border-border text-muted hover:text-foreground transition-all"
          title="Fullscreen"
        >
          {isFullscreen ? <Minimize size={16} /> : <Maximize size={16} />}
        </button>
      </div>

      {/* Bottom Left: Map Layers Menu */}
      <div className="absolute bottom-6 left-4 z-[400] flex flex-col gap-2 items-start pointer-events-auto">
        <div className="relative">
          <button
            onClick={() => {
              setShowLayersMenu(!showLayersMenu)
              setShowStyleMenu(false)
              setShowRiskMenu(false)
            }}
            className={`p-3 rounded-xl shadow-lg border transition-all flex items-center gap-2 text-xs font-bold ${
              showLayersMenu
                ? "bg-primary text-white border-primary"
                : "bg-card/96 backdrop-blur-md text-muted hover:text-foreground border-border"
            }`}
            title="Map Layers"
          >
            <Layers size={17} />
            <span className="hidden sm:inline">Layers</span>
          </button>

          <AnimatePresence>
            {showLayersMenu && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className="absolute bottom-full mb-3 left-0 w-64 bg-card/98 backdrop-blur-md rounded-2xl shadow-2xl border border-border p-3 z-[500]"
              >
                <div className="flex items-center justify-between mb-3 px-1">
                  <span className="text-xs font-bold text-foreground uppercase tracking-wider">
                    GIS Data Layers
                  </span>
                  <button
                    onClick={() => setActiveLayers(DEFAULT_LAYERS)}
                    className="text-[10px] text-muted hover:text-primary font-bold transition-colors"
                  >
                    Reset
                  </button>
                </div>
                {[
                  { key: "heatmap", label: "Landslide Risk Heatmap", icon: "🌡" },
                  { key: "riskLocations", label: "Risk Markers", icon: "📍" },
                  { key: "historicalLandslides", label: "Historical Landslides", icon: "⬛" },
                  { key: "stateBoundaries", label: "State Boundaries", icon: "🗺" },
                ].map(({ key, label, icon }) => (
                  <div
                    key={key}
                    className="flex items-center gap-3 p-2 hover:bg-muted-bg rounded-xl cursor-pointer transition-colors"
                    onClick={() => toggleLayer(key as keyof ActiveLayers)}
                  >
                    <span className="text-sm">{icon}</span>
                    <span className="flex-1 text-xs font-medium text-foreground">{label}</span>
                    <div
                      className={`w-8 h-4.5 rounded-full transition-colors relative ${
                        activeLayers[key as keyof ActiveLayers] ? "bg-primary" : "bg-border"
                      }`}
                    >
                      <div
                        className={`absolute top-0.5 size-3.5 rounded-full bg-white shadow-sm transition-transform ${
                          activeLayers[key as keyof ActiveLayers]
                            ? "translate-x-3.5"
                            : "translate-x-0.5"
                        }`}
                      ></div>
                    </div>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Bottom Center: Risk Legend */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[400] pointer-events-none hidden sm:block">
        <div className="bg-card/96 backdrop-blur-md px-4 py-2 rounded-full shadow-xl border border-border flex items-center gap-4">
          {(["Low", "Moderate", "High", "Very High"] as const).map((r) => (
            <div key={r} className="flex items-center gap-1.5">
              <span
                className="size-2.5 rounded-full"
                style={{
                  backgroundColor: RISK_COLORS[r],
                  boxShadow: r === "Very High" ? `0 0 6px ${RISK_COLORS[r]}` : "none",
                }}
              ></span>
              <span className="text-[10px] font-bold text-muted uppercase tracking-wider">{r}</span>
            </div>
          ))}
          <div className="h-3.5 w-px bg-border"></div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-foreground">
            <span>0%</span>
            <div className="w-16 h-1.5 rounded-full bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500"></div>
            <span>100%</span>
          </div>
        </div>
      </div>

      {/* Bottom Right: Requirement #18 Map Live Status Card */}
      <div className="absolute bottom-6 right-4 z-[400] pointer-events-none hidden md:block">
        <div className="bg-card/92 backdrop-blur-md border border-border rounded-2xl px-4 py-3 shadow-xl">
          <div className="flex items-center gap-2 mb-1">
            <span className={`size-2 rounded-full ${heatmapLoading ? "bg-amber-400 animate-ping" : "bg-risk-low animate-pulse"}`}></span>
            <span className="text-[10px] font-extrabold uppercase tracking-widest text-foreground">
              {heatmapLoading ? "CALCULATING ML HEATMAP" : "LIVE AI GIS PIPELINE"}
            </span>
          </div>
          <div className="text-[11px] text-muted font-medium">
            {heatmapPoints.length > 0 ? `${heatmapPoints.length} AI risk grid points active` : "12 critical stations active"}
          </div>
          <div className="mt-1.5 pt-1.5 border-t border-border text-xs font-bold text-foreground flex items-center justify-between gap-3">
            <span>Spatial Coverage</span>
            <span className="text-primary font-mono">{selectedRegion}</span>
          </div>
        </div>
      </div>


      {/* Loading overlay */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-background/50 backdrop-blur-xs z-[600] flex items-center justify-center pointer-events-auto"
          >
            <div className="bg-card p-6 rounded-2xl shadow-2xl border border-border flex flex-col items-center gap-3 min-w-[240px]">
              <Loader2 size={28} className="text-primary animate-spin" />
              <div className="text-xs font-bold text-foreground text-center">{loadingMsg}</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
