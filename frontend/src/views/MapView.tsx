import React from "react"
import { AnimatePresence } from "framer-motion"
import { LocationData, HistoricalEvent } from "../types"
import RealRiskMap from "../components/map/RealRiskMap"
import LocationRiskDetailsDrawer from "../components/drawers/LocationRiskDetailsDrawer"

export default function MapView({
  locations,
  historicalEvents,
  selectedLocationId,
  selectedRegion,
  setSelectedLocationId,
  addToast,
}: {
  locations: LocationData[]
  historicalEvents: HistoricalEvent[]
  selectedLocationId: number | null
  selectedRegion: string
  setSelectedLocationId: (id: number | null) => void
  addToast: (msg: string, type?: "success" | "error") => void
}) {
  const selectedLoc = locations.find((l) => l.id === selectedLocationId)

  return (
    <div className="relative w-full h-full overflow-hidden">
      <RealRiskMap
        locations={locations}
        historicalEvents={historicalEvents}
        selectedLocationId={selectedLocationId}
        selectedRegion={selectedRegion}
        onSelectLocation={setSelectedLocationId}
        addToast={addToast}
      />

      <AnimatePresence>
        {selectedLocationId !== null && selectedLoc && (
          <LocationRiskDetailsDrawer
            location={selectedLoc}
            onClose={() => setSelectedLocationId(null)}
            addToast={addToast}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
