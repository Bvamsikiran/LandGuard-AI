IMPORTANT: DO NOT REBUILD THE EXISTING UI FROM SCRATCH.

Keep the current LANDGUARD AI design system, sidebar, header, typography, spacing, colors, cards and overall visual style.

I already have a working basic UI. Now perform a SECOND-PASS UI/UX REFINEMENT focused on making the product feel like a real AI-powered GIS landslide early-warning system.

The current screens are:
1. Dashboard
2. Risk Map
3. Alerts

Keep these screens and improve them rather than replacing them.

==================================================
1. FIX THE MAIN PRODUCT FLOW
==================================================

The most important demo flow must be:

Dashboard
→ Risk Map
→ Search/select location
→ Click high-risk map marker
→ Location Risk Details side panel
→ Explain Why This Risk
→ Historical Landslides
→ Subscribe to Alerts

Make this flow extremely obvious and smooth.

The Risk Map should remain the HERO feature of the application.

==================================================
2. IMPROVE THE RISK MAP
==================================================

Keep the current realistic satellite/GIS map.

Improve it so it looks like a professional geospatial risk-monitoring system.

Add:

TOP MAP TOOLBAR:
- Search Location
- Search button
- Current Location button
- Refresh Risk Data button
- Layers button

RIGHT SIDE:
Risk filter control:
- All
- Low
- Moderate
- High
- Very High

MAP LAYERS PANEL:
Create a small floating layer control containing:
☑ Landslide Risk Heatmap
☑ Risk Locations
☐ Historical Landslides
☐ Rivers
☐ Roads
☐ Terrain / Elevation

Add a clear map legend at the bottom:
GREEN = LOW
YELLOW = MODERATE
ORANGE = HIGH
RED = VERY HIGH

Improve map markers:
- Low: green circular marker
- Moderate: yellow circular marker
- High: orange marker
- Very High: red marker with subtle pulsing animation

The Very High marker should be visually obvious because it is the primary demo interaction.

When hovering over a marker:
show a small tooltip:

"Sector 4, Green Valley"
"Risk Probability: 87%"
"VERY HIGH"

When clicking a marker:
open the Location Risk Details panel from the RIGHT side.

==================================================
3. CREATE / IMPROVE LOCATION RISK DETAILS PANEL
==================================================

This is the most important missing piece.

Create a polished right-side sliding panel that overlays the map without completely hiding it.

Header:

Location Risk Analysis
Sector 4, Green Valley

Latitude: 47.XXX
Longitude: -122.XXX

Show a large circular prediction visualization:

87%
Risk Probability

VERY HIGH RISK

Use RED only for Very High Risk.

Add a small timestamp:
"Prediction updated 2 minutes ago"

==================================================
4. ADD AI EXPLANATION
==================================================

Create a section:

"Why is this location at risk?"

Show:

Major Contributing Factors

24h Rainfall          31%
████████████████

Soil Moisture         24%
████████████

Slope Steepness       18%
█████████

Historical Landslides  9%
████

Elevation              8%

Use clean horizontal progress bars.

Add a button:

"View AI Explanation"

When clicked, show a concise explanation:

"High rainfall combined with elevated soil moisture and steep terrain significantly increases the predicted landslide probability at this location."

Add a small label:

"AI Explanation • SHAP-based feature importance"

Make this section visually impressive because explainable AI is an important judging point.

==================================================
5. ADD TERRAIN / GIS INFORMATION
==================================================

Inside the location details panel, add a compact:

"GEO-SPATIAL FEATURES"

Display cards:

Elevation
842 m

Slope
32°

Aspect
145°

Curvature
-0.21

Distance to River
350 m

Land Cover
Forest

This makes the GIS contribution visible in the demo.

Do NOT make this section huge.
Use compact cards or a 2-column grid.

==================================================
6. HISTORICAL LANDSLIDE SECTION
==================================================

Add a button:

"View Historical Landslides"

When clicked, show a small map/modal or expandable section displaying:

Historical Landslides Nearby

• Landslide Event — 2025
  420 m away

• Landslide Event — 2023
  680 m away

• Landslide Event — 2021
  1.2 km away

Show historical points on the map using a different icon/style from current risk markers.

==================================================
7. ADD ACTION BUTTONS
==================================================

At the bottom of the Location Risk Details panel:

Primary button:
"Subscribe to Alerts"

Secondary buttons:
"View Historical Landslides"
"Share Risk Report"

After clicking Subscribe:

Change button to:

✓ Alerts Subscribed

Make this interaction visually clear.

==================================================
8. IMPROVE DASHBOARD
==================================================

Keep the existing dashboard but make it more informative.

Current cards are good.

Improve them to:

OVERALL RISK
Moderate
3 areas elevated

ACTIVE ALERTS
12
2 Very High • 10 High

LOCATIONS MONITORED
1,248
Last 24 hours

MODEL STATUS
Active
94.2% Accuracy

Add a small trend indicator where appropriate.

For example:

↑ 12% from yesterday

Keep the numbers realistic-looking but clearly prototype/demo data.

==================================================
9. IMPROVE CURRENT RISK OVERVIEW
==================================================

Keep the map card.

Add:

Risk Heatmap

small legend:
Low | Moderate | High | Very High

Add a clear button:

"Open Interactive Risk Map →"

Make it look clickable.

Add a small overlay:

"1248 locations analyzed"
"12 active high-risk alerts"

==================================================
10. IMPROVE RECENT HIGH-RISK LOCATIONS
==================================================

Keep the current cards.

Improve them to show:

Sector 4, Green Valley
VERY HIGH
87% probability
↑ +12%

North Ridge Highway
HIGH
72% probability
↑ +5%

Pine Hill Sector
MODERATE
45% probability
↓ -2%

Clicking any location should open the Location Risk Details panel.

==================================================
11. IMPROVE ALERTS SCREEN
==================================================

Keep the existing Alerts screen structure.

Improve the alert cards.

Each alert should show:

Risk icon
Location
Risk badge
Probability
Time
Status

Example:

⚠ Sector 4, Green Valley
VERY HIGH
Probability: 87%
10 mins ago
Status: Active

Buttons:

View Details
Acknowledge

When Acknowledge is clicked:
change:

Status: Active

to:

✓ Status: Acknowledged

and visually reduce the alert emphasis.

==================================================
12. ADD ALERT FILTER
==================================================

The Filter Alerts button should open a small dropdown/popover:

Risk Level:
☐ Very High
☐ High
☐ Moderate
☐ Low

Area:
All Districts

Status:
☐ Active
☐ Acknowledged

Add:

Apply Filters
Clear Filters

==================================================
13. ADD LOADING STATES
==================================================

Create realistic loading states for:

Prediction
Heatmap
Location search
Refreshing risk data

Example:

"Analyzing location..."

with a subtle skeleton/loading animation.

After loading:

"Prediction complete"

This makes the AI interaction feel real during the demo.

==================================================
14. ADD SUCCESS / ERROR STATES
==================================================

Create toast notifications.

Examples:

✓ Risk prediction updated
✓ Alert subscription successful
✓ Alert acknowledged
✓ Risk data refreshed

Error:

⚠ Unable to fetch latest risk data

Keep them small and professional.

==================================================
15. IMPROVE VISUAL HIERARCHY
==================================================

Do NOT add excessive gradients or flashy effects.

Maintain:

Dark navy sidebar
White/light workspace
Blue primary action color
Green / Yellow / Orange / Red risk colors

Use red ONLY for:
- Very High risk
- Critical alerts
- warning states

Use subtle shadows and rounded corners.

Make primary buttons clearly distinguishable from secondary buttons.

==================================================
16. IMPORTANT GIS VISUAL DETAILS
==================================================

Make the map look like a genuine GIS interface.

Add subtle:

- Roads
- Rivers
- Terrain
- Historical landslide points
- Risk zones

Do not make the map visually overwhelming.

The risk heatmap should be the dominant visual layer.

==================================================
17. CREATE INTERACTION PROTOTYPE
==================================================

Connect the screens and interactions:

Dashboard
→ View Risk Map

Risk Map
→ Click marker
→ Location Risk Details panel

Location Details
→ Why This Risk
→ Historical Landslides
→ Subscribe to Alerts

Risk Map
→ Search Location
→ Show prediction

Risk Map
→ Risk filter

Alerts
→ View Details
→ Location Risk Details

Alerts
→ Acknowledge
→ Status changes to Acknowledged

Dashboard
→ Recent high-risk location
→ Location Risk Details

==================================================
18. DEMO-READY PRESENTATION
==================================================

The final prototype should communicate this story immediately:

"Where is the risk?"
→ GIS Risk Map

"How much is the risk?"
→ 87% probability

"Why is it risky?"
→ AI contributing factors

"What geographical conditions caused it?"
→ Elevation, slope, aspect, curvature, river distance, land cover

"Has this happened before?"
→ Historical landslides

"What should authorities do?"
→ Alerts + Acknowledge + Subscribe

Make these answers visually obvious.

IMPORTANT:
Do not remove existing good components.
Do not create unnecessary pages.
Do not redesign the entire application.
Refine the existing implementation and add the missing interactions and Location Risk Details panel.

Prioritize:
1. Risk Map
2. Location Risk Details
3. AI Explanation
4. GIS Features
5. Alerts interactions
6. Dashboard polish