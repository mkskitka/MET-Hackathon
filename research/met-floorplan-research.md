# Met Museum Floorplan & Gallery Layout Research

## Summary

We successfully reverse-engineered the Met's interactive map at maps.metmuseum.org. The map is built on **Mapbox GL JS** with data served by **Living Map** (livingmap.com). We extracted:

- **443 gallery room polygons** with real lat/lng geometry across all floors
- **34 section/wing area polygons** (departments like "Egyptian Art", "The American Wing")
- **315 other room polygons** (corridors, restrooms, shops, cafes, etc.)
- **248 gallery metadata records** from the search API (names, descriptions, images)
- **792 total features** in the complete floorplan GeoJSON

All data is saved as GeoJSON files ready for use.

---

## Extracted Data Files

| File | Description | Features |
|------|-------------|----------|
| `gallery_rooms.geojson` | Gallery room polygons with floor/name data | 443 |
| `section_areas.geojson` | Wing/department area polygons | 34 |
| `other_rooms.geojson` | Corridors, restrooms, shops, etc. | 315 |
| `met_complete_floorplan.geojson` | Everything combined | 792 |
| `all_galleries.json` | Gallery metadata from API (descriptions, images) | 283 |
| `gallery_points.json` | Simplified gallery center points | 248 |
| `feature_names.json` | All feature names from the API | 339 |

### Gallery Distribution by Floor

| Floor | Gallery Count |
|-------|--------------|
| Floor G | 6 |
| Floor 1 | 202 |
| Floor 1M | 10 |
| Floor 2 | 208 |
| Floor 3 | 16 |
| Floor 5 | 1 |

---

## Data Sources Discovered

### 1. Living Map API (Public, No Auth Required)

**Base URL:** `https://map-api.prod.livingmap.com/v1/maps/the_met`

**Key endpoints:**
- `GET /v1/maps?host=maps.metmuseum.org` - Full map config (floors, regions, zoom, Mapbox token, etc.)
- `GET /v1/maps/the_met/styles/styles.json` - Mapbox style spec with tile source URLs and layer definitions
- `GET /v1/maps/the_met/feature-names?lang=en-GB` - All 339 feature names
- `GET /v1/maps/the_met/search?query={q}&latitude=40.779448&longitude=-73.963517&limit=50&lang=en-GB&floor_id={id}` - Search features
- `GET /v1/maps/the_met/search/tag/{tagId}?latitude=...&longitude=...&limit=50&floor_id={id}` - Search by tag
- `GET /v1/maps/the_met/features/{featureId}` - Single feature detail
- `GET /v1/maps/the_met/features/?long_name={name}&lang=en-GB` - Feature by name
- `GET /v1/maps/the_met/features-uid/{uid}` - Feature by UID
- `GET /v1/maps/the_met/geofences?limit=50` - Geofence boundaries (currently empty)

**Map config:**
- Map ID: `the_met`
- Mapbox access token: `pk.eyJ1IjoibGl2aW5nbWFwIiwiYSI6ImNsZTVnd2poZzA5ankzdnM0dG1jc3VlNDEifQ.-tXvkTQ4ZWSPwGfP2UyouA`
- Center: 40.779448, -73.963517
- Bearing: -61 degrees
- Zoom: min 11, max 21, default 17
- Timezone: America/New_York

**Floor IDs:**
| ID | Level | Name |
|----|-------|------|
| 1 | 0.0 | Floor G |
| 2 | 1.0 | Floor 1 (default) |
| 3 | 1.5 | Floor 1M |
| 4 | 2.0 | Floor 2 |
| 5 | 3.0 | Floor 3 |
| 6 | 4.0 | Floor 4 |
| 7 | 5.0 | Floor 5 |

**Search tags:**
| ID | Name |
|----|------|
| 4 | Restrooms |
| 5 | Dining |
| 6 | Retail |
| 7 | Lactation Room |
| 8 | Water Fountains |
| 9 | Information Desk |

**Regions (with GeoJSON polygons):**
- The Met Cloisters (40.864, -73.932)
- The Met Fifth Avenue (40.779, -73.964)

### 2. Vector Tiles (Room Polygon Geometry)

**Tile URL:** `https://prod.cdn.livingmap.com/tiles/the_met/{z}/{x}/{y}.pbf?lang=en-GB`

Format: Mapbox Vector Tiles (MVT/protobuf), standard `{z}/{x}/{y}` scheme.

**Tile sources:**
- `lm` source: `https://prod.cdn.livingmap.com/tiles/the_met/{z}/{x}/{y}.pbf?lang=en-GB` (zoom 0-19)
- `lm_osm` source: `https://prod.cdn.livingmap.com/the_met_basemap/{z}/{x}/{y}` (zoom 0-16)
- Sprite: `https://prod.cdn.livingmap.com/styles/the_met/icons`
- Glyphs: `https://prod.cdn.livingmap.com/fonts/{fontstack}/{range}.pbf`

**Layers in tiles:**
- `indoor` - All indoor features (~3500-4800 features per tile)
- `outdoor` - Building outline and label

**Indoor feature categories (from vector tiles):**
| Category | Class | Type | Count | Geometry |
|----------|-------|------|-------|----------|
| room | tourism | gallery | 571 | Polygon, MultiPolygon, Point |
| barrier | building | door | 683 | LineString |
| barrier | building | wall | 612 | LineString |
| barrier | circulation | stairs | 421 | LineString |
| barrier | building | partition | 246 | LineString |
| barrier | building | threshold | 196 | LineString |
| object | building | column | 99 | Polygon |
| room | building | back_of_house | 95 | Polygon, Point |
| room | building | corridor | 93 | Polygon |
| unit | circulation | lift | 64 | Polygon, Point |
| area | building | section | 54 | Polygon, Point |

**Gallery polygon properties:**
```json
{
  "geom_id": 3422,
  "category": "room",
  "class": "tourism",
  "type": "gallery",
  "name": "599",
  "popup_header": "Special Exhibitions",
  "popup_subheader": "Gallery 599",
  "popup_body": "This gallery has no description.",
  "popup_image_url": "https://cdn.sanity.io/images/...",
  "floor_id": 1,
  "floor_level": "0.0",
  "floor_name": "Floor G",
  "location_name": "The Met Fifth Avenue",
  "lm_id": "85ba985015a0df1f5e14174588bf3310",
  "uid": 970548128399
}
```

### 3. Met Collection API (Artwork Data)

**Base URL:** `https://collectionapi.metmuseum.org/public/collection/v1/`
- No auth required, 80 req/sec limit
- `GET /objects/{id}` returns `GalleryNumber` field
- `GET /search?isOnView=true&q=*` finds on-view objects
- `GET /departments` lists all 19 departments

The `GalleryNumber` field in artwork records matches the gallery numbers in our extracted polygons (e.g., "822" = Gallery 822).

---

## Architecture

```
Living Map API ──→ Map config, floor IDs, feature metadata (names, descriptions, images)
     │
Vector Tiles ───→ Room polygon geometry (lat/lng boundaries for every room)
     │
Met Collection API → Artwork data with GalleryNumber field
     │
     └──→ JOIN on gallery_number to link rooms ↔ artworks
```

**Join key:** `gallery_number` from vector tiles = `GalleryNumber` from Met Collection API

---

## Sections/Wings (from vector tiles)

| Floor | Section Name |
|-------|-------------|
| Floor G | Robert Lehman Collection |
| Floor G | Ruth and Harold D. Uris Center for Education |
| Floor G | The Costume Institute |
| Floor 1 | Egyptian Art |
| Floor 1 | The American Wing |
| Floor 1 | Greek and Roman Art |
| Floor 1 | Robert Lehman Wing |
| Floor 1 | Modern and Contemporary Art |
| Floor 1 | Arms and Armor |
| Floor 1 | Medieval Art |
| Floor 1 | The Great Hall |
| Floor 1 | European Sculpture and Decorative Arts |
| Floor 1 | Arts of Oceania |
| Floor 1 | Arts of Africa |
| Floor 1 | Arts of the Ancient Americas |
| Floor 1 | Michael C. Rockefeller Wing |
| Floor 1M | The American Wing |
| Floor 1M | Modern and Contemporary Art |
| Floor 1M | Greek and Roman Art |
| Floor 2 | The American Wing |
| Floor 2 | 19th and Early 20th Century European Paintings and Sculpture |
| Floor 2 | Art of the Arab Lands, Turkey, Iran, Central Asia, and Later South Asia |
| Floor 2 | Asian Art |
| Floor 2 | Photographs |
| Floor 2 | Drawings, Prints, and Photographs |
| Floor 2 | Musical Instruments |
| Floor 2 | European Paintings, 1250-1800 |
| Floor 2 | Modern and Contemporary Art |
| Floor 2 | Drawings and Prints |
| Floor 2 | Art of Ancient West Asia and the Art of Ancient Cyprus |
| Floor 2 | European Sculpture and Decorative Arts |
| Floor 3 | The American Wing |
| Floor 3 | Asian Art |
| Floor 5 | The Iris and B.Gerald Cantor Roof Garden |

---

## Departments (from Met Collection API)

| ID | Department |
|----|-----------|
| 1 | American Decorative Arts |
| 3 | Ancient West Asian Art |
| 4 | Arms and Armor |
| 5 | Arts of Africa, Oceania, and the Americas |
| 6 | Asian Art |
| 7 | The Cloisters |
| 8 | The Costume Institute |
| 9 | Drawings and Prints |
| 10 | Egyptian Art |
| 11 | European Paintings |
| 12 | European Sculpture and Decorative Arts |
| 13 | Greek and Roman Art |
| 14 | Islamic Art |
| 15 | The Robert Lehman Collection |
| 16 | The Libraries |
| 17 | Medieval Art |
| 18 | Musical Instruments |
| 19 | Photographs |
| 21 | Modern Art |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `fetch_galleries.py` | Fetches gallery metadata from Living Map search API |
| `decode_tile.py` | Downloads and decodes vector tiles from the tile server |
| `extract_rooms_v2.py` | Extracts room polygons from tiles, converts to GeoJSON |

Run with: `source .venv/bin/activate && python3 research/<script>.py`

Dependencies: `mapbox-vector-tile` (installed in `.venv`)
