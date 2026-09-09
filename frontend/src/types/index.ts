export type View =
  | "dashboard"
  | "map"
  | "alerts"
  | "analysis"
  | "historical"
  | "reports"
  | "insights"
  | "status"
  | "settings"

export type RiskLevel = "Low" | "Moderate" | "High" | "Very High"

export type MapStyle = "satellite" | "terrain" | "streets" | "light"

export type ThemeMode = "dark" | "light" | "system"

export type ActiveLayers = {
  heatmap: boolean
  riskLocations: boolean
  historicalLandslides: boolean
  rivers: boolean
  roads: boolean
  terrain: boolean
  stateBoundaries: boolean
}

export type LocationData = {
  id: number
  name: string
  shortName: string
  state: string
  district: string
  lat: number
  lon: number
  risk: RiskLevel
  prob: number
  change: string
  elevation: number
  slope: number
  aspect: number
  curvature: number
  riverDist: number
  landCover: string
  soilType: string
  geology: string
  rainfall24h: number
  soilMoisture: number
  historicalNearby: number
}

export type Alert = {
  id: number
  locationId: number
  location: string
  state: string
  district: string
  level: RiskLevel
  prob: string
  time: string
  status: "Active" | "Acknowledged" | "Resolved"
  description?: string
}

export type HistoricalEvent = {
  id: number
  name: string
  state: string
  district: string
  lat: number
  lon: number
  date: string
  year: number
  severity: RiskLevel
  trigger: string
  casualties: number
  affectedRoads: string
}

export type FieldReport = {
  id: string
  locationName: string
  state: string
  lat: number
  lon: number
  hazardType: "Slope Movement" | "Road Crack" | "Rockfall" | "Debris Flow" | "Mudslide"
  severity: RiskLevel
  description: string
  photoUrl?: string
  reporterName: string
  timestamp: string
  status: "Pending Verification" | "Verified" | "Action Taken"
}

export type UserProfile = {
  name: string
  role: string
  email: string
  organization: string
  avatarUrl?: string
}

export type AppSettings = {
  notifications: {
    emailAlerts: boolean
    pushAlerts: boolean
    criticalOnly: boolean
    soundEnabled: boolean
  }
  map: {
    defaultStyle: MapStyle
    defaultZoom: number
    autoRefresh: boolean
    refreshIntervalSeconds: number
    showHeatmap: boolean
    showHistorical: boolean
    showRivers: boolean
    showRoads: boolean
    showTerrain: boolean
  }
  riskMonitoring: {
    defaultThreshold: RiskLevel
    predictionInterval: string
    showProbability: boolean
    showExplanations: boolean
  }
  appearance: {
    theme: ThemeMode
    compactSidebar: boolean
    highContrast: boolean
  }
}
