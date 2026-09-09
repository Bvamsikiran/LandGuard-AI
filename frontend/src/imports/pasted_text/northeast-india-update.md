IMPORTANT MAP CORRECTION:

The current prototype incorrectly uses "Pacific Northwest Region" and a Pacific Northwest-looking satellite map.

Our actual project study region is NORTHEAST INDIA.

Modify the existing application to use Northeast India as the default geographic region.

DO NOT rebuild the UI.
DO NOT change the existing design system.
DO NOT remove existing interactions.

Only replace the geographic context and sample location data.

==================================================
STUDY REGION
==================================================

Default location:

"Northeastern India"

The primary region should cover:

- Arunachal Pradesh
- Assam
- Manipur
- Meghalaya
- Mizoram
- Nagaland
- Sikkim
- Tripura

Default map should be centered on Northeast India.

Use approximately:

Latitude: 26° N
Longitude: 93° E

Set an appropriate zoom level so the Northeast India region is clearly visible.

==================================================
HEADER
==================================================

Replace:

"Pacific Northwest Region"

with:

"Northeastern India"

Location dropdown should contain:

Northeastern India ✓
Arunachal Pradesh
Assam
Manipur
Meghalaya
Mizoram
Nagaland
Sikkim
Tripura

When a state is selected, update the map view accordingly.

==================================================
MAP
==================================================

Replace the current Pacific Northwest map imagery with a map centered on Northeast India.

The map should visually represent:

Northeast India
India state boundaries
Roads
Rivers
Terrain
Risk zones
Landslide locations

The main map should look like a GIS disaster-management map.

Use Northeast India geography rather than North American geography.

==================================================
RISK LOCATIONS
==================================================

Use realistic-looking DEMO locations based on the project's supplied dataset.

Example locations:

Arunachal Pradesh
Assam
Manipur
Meghalaya
Mizoram
Nagaland
Sikkim
Tripura

Use the latitude and longitude values from the project's dataset when possible.

Do NOT use:
- Seattle
- Washington
- Oregon
- California
- Pacific Northwest locations

==================================================
RISK MARKERS
==================================================

Display risk markers across Northeast India.

Use:

GREEN = LOW
YELLOW = MODERATE
ORANGE = HIGH
RED = VERY HIGH

Include several high-risk and very-high-risk locations.

Example:

Arunachal Pradesh
VERY HIGH
87%

Nagaland
HIGH
72%

Meghalaya
MODERATE
45%

These are DEMO values and should be treated as prototype data.

==================================================
HISTORICAL LANDSLIDES
==================================================

Historical landslide markers should also be located in Northeast India.

Use the project's supplied historical landslide dataset for the prototype where possible.

Historical events include locations in:

Arunachal Pradesh
Assam
Manipur
Meghalaya
Mizoram
Nagaland
Sikkim
Tripura

Use a visually distinct marker for historical landslides.

==================================================
GIS LAYERS
==================================================

The Layers control should contain:

☑ Landslide Risk Heatmap
☑ Risk Locations
☐ Historical Landslides
☐ Rivers
☐ Roads
☐ Terrain / Elevation
☐ State Boundaries

When toggled, visually change the map layer state.

==================================================
LOCATION DETAILS
==================================================

When clicking a risk marker, open the existing Location Risk Details panel.

Use Northeast India sample data.

Example:

Location:
Arunachal Pradesh

Risk Probability:
87%

Risk Level:
VERY HIGH

GIS FEATURES:

Elevation:
842 m

Slope:
32°

Aspect:
145°

Curvature:
-0.21

Distance to River:
350 m

Land Cover:
Forest

Historical Landslides:
8 nearby

These values are DEMO/PROTOTYPE values.

==================================================
DASHBOARD
==================================================

Change:

"Pacific Northwest Region"

to:

"Northeastern India"

Change location names throughout the dashboard to Northeast India examples.

Recent High-Risk Locations could include:

Arunachal Pradesh
VERY HIGH
87%

Nagaland
HIGH
72%

Meghalaya
MODERATE
45%

Do not use Green Valley / North Ridge Highway unless they are clearly presented as fictional local labels.

==================================================
ALERTS
==================================================

Use Northeast India locations.

Example:

VERY HIGH
Arunachal Pradesh
Probability: 87%

HIGH
Nagaland
Probability: 72%

MODERATE
Meghalaya
Probability: 45%

Keep the existing alert interactions.

==================================================
SEARCH
==================================================

Search examples should use Northeast India locations.

Placeholder:

"Search location in Northeast India..."

Example suggestions:

Itanagar, Arunachal Pradesh
Guwahati, Assam
Imphal, Manipur
Shillong, Meghalaya
Aizawl, Mizoram
Kohima, Nagaland
Gangtok, Sikkim
Agartala, Tripura

Selecting a location should center the map and show the corresponding risk prediction.

==================================================
IMPORTANT
==================================================

The supplied project ZIP contains the project's demo datasets.

Use its geographic context consistently.

The project data contains latitude/longitude and GIS attributes such as:

elevation
slope
aspect
curvature
distance to river
drainage density
land cover
soil
geology
historical landslides

The prototype should visually communicate that these GIS features contribute to the AI landslide prediction.

Do not claim the supplied synthetic data is real-world measured data.

FINAL REQUIREMENT:

The entire application must consistently represent:

"AI-Powered Landslide Risk Prediction for Northeast India"

There must be NO remaining references to:

Pacific Northwest
Seattle
Washington
Oregon
or other unrelated North American geography.

Keep all existing buttons, navigation and interactions working after this modification.