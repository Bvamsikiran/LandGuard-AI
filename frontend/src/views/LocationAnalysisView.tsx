import React, { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Compass, Globe, BarChart2, ChevronRight, Activity, AlertCircle } from "lucide-react"
import { LocationData } from "../types"
import RiskBadge from "../components/common/RiskBadge"
import FactorBar from "../components/common/FactorBar"
import GisCard from "../components/common/GisCard"

export default function LocationAnalysisView({
  locations,
  selectedRegion,
  onNavigateToMap,
}: {
  locations: LocationData[]
  selectedRegion: string
  onNavigateToMap: (locId: number) => void
}) {
  const regionLocations =
    selectedRegion === "Northeastern India"
      ? locations
      : locations.filter((l) => l.state.toLowerCase() === selectedRegion.toLowerCase())

  const [selectedId, setSelectedId] = useState<number>(regionLocations[0]?.id || 1)

  useEffect(() => {
    if (regionLocations.length > 0 && !regionLocations.find((l) => l.id === selectedId)) {
      setSelectedId(regionLocations[0].id)
    }
  }, [selectedRegion, regionLocations, selectedId])

  const loc = regionLocations.find((l) => l.id === selectedId) || regionLocations[0]

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Location Risk Analysis</h1>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            Spatial Terrain & Environmental Breakdown — {selectedRegion}
          </p>
        </div>

        {regionLocations.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-xs font-bold text-muted uppercase">Select Location:</label>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(Number(e.target.value))}
              className="text-xs sm:text-sm bg-card border border-border font-bold rounded-xl px-3.5 py-2 outline-none text-foreground cursor-pointer shadow-xs"
            >
              {regionLocations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.risk})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {regionLocations.length === 0 ? (
        <div className="bg-card rounded-2xl border border-border p-12 text-center space-y-3">
          <div className="size-12 rounded-full bg-muted-bg flex items-center justify-center mx-auto text-muted">
            <AlertCircle size={24} />
          </div>
          <h3 className="font-bold text-base text-foreground">
            No monitored locations available for this region.
          </h3>
          <p className="text-xs text-muted max-w-md mx-auto">
            Select another state or "Northeastern India" from the region header dropdown to view location GIS analysis.
          </p>
        </div>
      ) : (
        <>
          {/* Selected Location Card */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-card rounded-2xl border border-border p-6 shadow-sm flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted flex items-center gap-1">
                    <Compass size={12} /> {loc.lat.toFixed(4)}°N, {loc.lon.toFixed(4)}°E
                  </span>
                  <RiskBadge level={loc.risk} />
                </div>
                <h2 className="text-2xl font-bold text-foreground mt-2">{loc.name}</h2>
                <p className="text-xs text-muted mt-0.5">District: {loc.district}</p>
              </div>

              <div className="bg-muted-bg/60 rounded-2xl p-5 border border-border flex items-center justify-between">
                <div>
                  <div className="text-[10px] uppercase font-bold text-muted tracking-wider">
                    Predicted Landslide Risk
                  </div>
                  <div className="text-4xl font-extrabold text-foreground tracking-tight mt-1">
                    {loc.prob}%
                  </div>
                  <div className="text-xs font-bold text-risk-high mt-1">{loc.change} vs 24h average</div>
                </div>
                <div className="size-16 rounded-full border-4 border-risk-high flex items-center justify-center font-bold text-risk-high text-sm">
                  {loc.risk.toUpperCase()}
                </div>
              </div>

              <button
                onClick={() => onNavigateToMap(loc.id)}
                className="w-full py-3 bg-primary text-white font-bold text-xs rounded-xl hover:bg-primary/90 transition flex items-center justify-center gap-1.5 shadow-md shadow-primary/20"
              >
                View on Interactive GIS Map <ChevronRight size={15} />
              </button>
            </div>

            {/* Factors Breakdown */}
            <div className="bg-card rounded-2xl border border-border p-6 shadow-sm flex flex-col justify-between space-y-4">
              <h3 className="font-bold text-sm text-foreground flex items-center gap-2 border-b border-border pb-3">
                <BarChart2 size={16} className="text-primary" /> SHAP Factor Importance Breakdown
              </h3>

              <div className="space-y-3.5 flex-1">
                <FactorBar label="24h Precipitation" percent={31} value={`${loc.rainfall24h} mm`} />
                <FactorBar label="Soil Moisture Saturation" percent={24} value={`${loc.soilMoisture}%`} />
                <FactorBar label="Slope Gradient" percent={18} value={`${loc.slope}°`} />
                <FactorBar label="Historical Susceptibility" percent={12} value={`${loc.historicalNearby} events`} />
                <FactorBar label="Elevation Altitude" percent={8} value={`${loc.elevation} m`} />
              </div>
            </div>

            {/* Environmental GIS Traits */}
            <div className="bg-card rounded-2xl border border-border p-6 shadow-sm space-y-4">
              <h3 className="font-bold text-sm text-foreground flex items-center gap-2 border-b border-border pb-3">
                <Globe size={16} className="text-primary" /> Terrain & Environmental GIS Traits
              </h3>

              <div className="grid grid-cols-2 gap-2.5">
                <GisCard label="Elevation" value={`${loc.elevation} m`} />
                <GisCard label="Slope Angle" value={`${loc.slope}°`} />
                <GisCard label="Aspect Orientation" value={`${loc.aspect}°`} />
                <GisCard label="Curvature Index" value={`${loc.curvature}`} />
                <GisCard label="Dist. to River" value={`${loc.riverDist} m`} />
                <GisCard label="Land Cover" value={loc.landCover} />
                <GisCard label="Soil Type" value={loc.soilType} />
                <GisCard label="Geology" value={loc.geology} />
              </div>
            </div>
          </div>

          {/* Comparison Table */}
          <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
            <div className="p-5 border-b border-border flex items-center justify-between">
              <h3 className="font-bold text-base text-foreground flex items-center gap-2">
                <Activity size={16} className="text-primary" /> Monitored Locations Comparative Matrix
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted-bg text-muted uppercase text-[10px] tracking-wider font-bold">
                  <tr>
                    <th className="p-4">Location</th>
                    <th className="p-4">State</th>
                    <th className="p-4">Risk Level</th>
                    <th className="p-4">Prob.</th>
                    <th className="p-4">Elevation</th>
                    <th className="p-4">Slope</th>
                    <th className="p-4">24h Rain</th>
                    <th className="p-4">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-medium">
                  {regionLocations.map((item) => (
                    <tr key={item.id} className="hover:bg-muted-bg/50 transition-colors">
                      <td className="p-4 font-bold text-foreground">{item.name}</td>
                      <td className="p-4 text-muted">{item.state}</td>
                      <td className="p-4">
                        <RiskBadge level={item.risk} small />
                      </td>
                      <td className="p-4 font-mono font-bold">{item.prob}%</td>
                      <td className="p-4 font-mono">{item.elevation} m</td>
                      <td className="p-4 font-mono">{item.slope}°</td>
                      <td className="p-4 font-mono text-primary font-bold">{item.rainfall24h} mm</td>
                      <td className="p-4">
                        <button
                          onClick={() => onNavigateToMap(item.id)}
                          className="text-xs text-primary font-bold hover:underline flex items-center gap-1"
                        >
                          Map <ChevronRight size={12} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
