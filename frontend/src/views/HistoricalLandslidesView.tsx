import React, { useState, useEffect } from "react"
import { motion } from "framer-motion"
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
} from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { History, Calendar, AlertTriangle, MapPin, Filter, Layers } from "lucide-react"
import { HistoricalEvent } from "../types"
import RiskBadge from "../components/common/RiskBadge"

function createHistoricalDivIcon() {
  const html = `
    <div style="width:16px; height:16px; background:#EF4444; border:2px solid white; transform: rotate(45deg); box-shadow:0 2px 6px rgba(0,0,0,0.5);"></div>
  `
  return L.divIcon({
    html,
    className: "custom-historical-marker",
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  })
}

function HistoricalMapController({ targetLatLon }: { targetLatLon?: { lat: number; lon: number } | null }) {
  const map = useMap()
  useEffect(() => {
    if (targetLatLon) {
      map.flyTo([targetLatLon.lat, targetLatLon.lon], 9, { duration: 1 })
    }
  }, [targetLatLon, map])
  return null
}

export default function HistoricalLandslidesView({
  events,
  selectedRegion,
  onNavigateToMap,
}: {
  events: HistoricalEvent[]
  selectedRegion: string
  onNavigateToMap: () => void
}) {
  const [selectedState, setSelectedState] = useState<string>(
    selectedRegion === "Northeastern India" ? "All" : selectedRegion
  )
  const [selectedSeverity, setSelectedSeverity] = useState<string>("All")
  const [targetLatLon, setTargetLatLon] = useState<{ lat: number; lon: number } | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)

  useEffect(() => {
    if (selectedRegion !== "Northeastern India") {
      setSelectedState(selectedRegion)
    }
  }, [selectedRegion])

  const filteredEvents = events.filter(
    (e) =>
      (selectedState === "All" || e.state.toLowerCase() === selectedState.toLowerCase()) &&
      (selectedSeverity === "All" || e.severity.toLowerCase() === selectedSeverity.toLowerCase())
  )

  const statesList = ["All", "Arunachal Pradesh", "Assam", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"]

  const handleSelectEvent = (evt: HistoricalEvent) => {
    setSelectedEventId(evt.id)
    setTargetLatLon({ lat: evt.lat, lon: evt.lon })
  }

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <History className="text-primary" size={24} /> Historical Landslides Database
          </h1>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            Archival Landslide Records & Spatial Incident Inventory — Northeast India
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Filter size={13} className="text-muted" />
            <span className="text-xs font-bold text-muted uppercase">State:</span>
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="text-xs sm:text-sm bg-card border border-border font-bold rounded-xl px-3 py-1.5 outline-none text-foreground cursor-pointer shadow-xs"
            >
              {statesList.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-muted uppercase">Severity:</span>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="text-xs sm:text-sm bg-card border border-border font-bold rounded-xl px-3 py-1.5 outline-none text-foreground cursor-pointer shadow-xs"
            >
              {["All", "Very High", "High", "Moderate"].map((sev) => (
                <option key={sev} value={sev}>
                  {sev}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Historical Interactive Leaflet Map */}
      <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm h-72 sm:h-80 relative">
        <div className="absolute top-3 left-3 z-[400] bg-card/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-border shadow-md flex items-center gap-2 text-xs font-bold text-foreground">
          <Layers size={14} className="text-primary" /> Historical Landslide Incident Map
        </div>

        <MapContainer
          center={[26.0, 93.0]}
          zoom={7}
          zoomControl={true}
          className="w-full h-full z-0"
        >
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Esri, Maxar, Earthstar Geographics"
          />

          <HistoricalMapController targetLatLon={targetLatLon} />

          {filteredEvents.map((evt) => (
            <Marker
              key={evt.id}
              position={[evt.lat, evt.lon]}
              icon={createHistoricalDivIcon()}
              eventHandlers={{
                click: () => handleSelectEvent(evt),
              }}
            >
              <Popup>
                <div className="p-1 font-sans max-w-xs">
                  <div className="font-bold text-xs text-foreground flex items-center gap-1">
                    <AlertTriangle size={13} className="text-risk-very-high" /> {evt.name}
                  </div>
                  <div className="text-[11px] text-muted mt-1">Date: {evt.date}</div>
                  <div className="text-[11px] text-muted">Trigger: {evt.trigger}</div>
                  <div className="text-[11px] text-muted font-bold text-risk-very-high mt-0.5">
                    Casualties: {evt.casualties}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {/* Events Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredEvents.length === 0 ? (
          <div className="col-span-full bg-card rounded-2xl border border-border p-8 text-center text-xs text-muted font-medium">
            No historical landslide records match the selected state or severity filters.
          </div>
        ) : (
          filteredEvents.map((evt) => {
            const isSelected = selectedEventId === evt.id
            return (
              <motion.div
                key={evt.id}
                whileHover={{ y: -2 }}
                onClick={() => handleSelectEvent(evt)}
                className={`bg-card border rounded-2xl p-5 shadow-xs transition-all space-y-3 cursor-pointer ${
                  isSelected ? "border-primary ring-2 ring-primary/30" : "border-border hover:border-primary/40"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono font-bold text-muted flex items-center gap-1 mb-1">
                      <Calendar size={11} /> {evt.date}
                    </span>
                    <h3 className="font-bold text-base text-foreground flex items-center gap-2">
                      <MapPin size={15} className="text-risk-high shrink-0" /> {evt.name}
                    </h3>
                    <div className="text-xs text-muted mt-0.5">
                      {evt.district}, {evt.state} · ({evt.lat.toFixed(2)}°N, {evt.lon.toFixed(2)}°E)
                    </div>
                  </div>
                  <RiskBadge level={evt.severity} />
                </div>

                <div className="bg-muted-bg/60 p-3 rounded-xl border border-border text-xs space-y-1.5 font-medium">
                  <div className="flex justify-between">
                    <span className="text-muted">Primary Trigger:</span>
                    <span className="font-bold text-foreground">{evt.trigger}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Impact:</span>
                    <span className="font-semibold text-foreground text-right">{evt.affectedRoads}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Casualties:</span>
                    <span className="font-bold text-risk-very-high">{evt.casualties} reported</span>
                  </div>
                </div>
              </motion.div>
            )
          })
        )}
      </div>
    </div>
  )
}
