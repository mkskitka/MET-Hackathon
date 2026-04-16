#!/usr/bin/env python3
"""
Extract gallery room polygons from Met vector tiles -> GeoJSON.
Uses z16 tiles (best positional accuracy without clipping).
Deduplicates by geom_id, keeping the polygon with the largest area.

TODO: Rooms 731-770 (American Wing upper floors) are extracted with incorrect
positions - they appear as floating clusters disconnected from the main building.
This is a tile coordinate precision issue. These rooms are currently excluded
in a post-processing step. To fix properly, their coordinates need to be
manually corrected or extracted from a different data source.
"""

import json
import math
import urllib.request
import mapbox_vector_tile

TILE_URL = "https://prod.cdn.livingmap.com/tiles/the_met/{z}/{x}/{y}.pbf?lang=en-GB"

def pixel_to_latlng(px, py, tile_x, tile_y, zoom, extent=4096):
    n = 2 ** zoom
    lng = (tile_x + px / extent) / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (tile_y + py / extent) / n)))
    lat = math.degrees(lat_rad)
    return lat, lng

def convert_coords(coords, tx, ty, z, ext):
    if isinstance(coords[0], (int, float)):
        lat, lng = pixel_to_latlng(coords[0], coords[1], tx, ty, z, ext)
        return [lng, lat]
    return [convert_coords(c, tx, ty, z, ext) for c in coords]

def convert_geometry(geom, tx, ty, z, ext=4096):
    return {"type": geom["type"], "coordinates": convert_coords(geom["coordinates"], tx, ty, z, ext)}

def count_vertices(geom):
    coords = geom["coordinates"]
    if geom["type"] == "Polygon":
        return sum(len(ring) for ring in coords)
    elif geom["type"] == "MultiPolygon":
        return sum(len(ring) for poly in coords for ring in poly)
    return 0

def polygon_area(ring):
    """Shoelace formula for polygon area."""
    n = len(ring)
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += ring[i][0] * ring[j][1]
        area -= ring[j][0] * ring[i][1]
    return abs(area) / 2

def geom_area(geom):
    """Compute total area of a geometry."""
    coords = geom["coordinates"]
    if geom["type"] == "Polygon":
        return polygon_area(coords[0])
    elif geom["type"] == "MultiPolygon":
        return sum(polygon_area(poly[0]) for poly in coords)
    return 0

def fetch_tile(z, x, y):
    url = TILE_URL.format(z=z, x=x, y=y)
    req = urllib.request.Request(url)
    req.add_header("Referer", "https://maps.metmuseum.org/")
    with urllib.request.urlopen(req) as resp:
        return mapbox_vector_tile.decode(resp.read())

def lat_lng_to_tile(lat, lng, zoom):
    n = 2 ** zoom
    x = int((lng + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def extract_from_tiles(zoom, tile_range):
    """Extract features from a set of tiles at given zoom."""
    galleries = {}
    sections = {}
    other_rooms = {}

    for tx, ty in tile_range:
        print(f"  Fetching z{zoom}/{tx}/{ty}...")
        try:
            decoded = fetch_tile(zoom, tx, ty)
        except Exception as e:
            print(f"    Failed: {e}")
            continue

        indoor = decoded.get("indoor", {})
        features = indoor.get("features", [])
        extent = indoor.get("extent", 4096)

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            geom_type = geom.get("type", "")
            cat = props.get("category", "")
            cls = props.get("class", "")
            typ = props.get("type", "")
            gid = props.get("geom_id", 0)

            if geom_type not in ("Polygon", "MultiPolygon"):
                continue

            geo = convert_geometry(geom, tx, ty, zoom, extent)
            verts = count_vertices(geo)

            if cat == "room" and cls == "tourism" and typ == "gallery":
                if gid not in galleries or geom_area(geo) > geom_area(galleries[gid]["geometry"]):
                    galleries[gid] = {
                        "type": "Feature",
                        "geometry": geo,
                        "properties": {
                            "geom_id": gid,
                            "gallery_number": props.get("name", ""),
                            "floor_id": props.get("floor_id", ""),
                            "floor_name": props.get("floor_name", ""),
                            "floor_level": props.get("floor_level", ""),
                            "location_name": props.get("location_name", ""),
                            "popup_header": props.get("popup_header", ""),
                            "popup_subheader": props.get("popup_subheader", ""),
                            "popup_body": props.get("popup_body", ""),
                            "popup_image_url": props.get("popup_image_url", ""),
                            "lm_id": props.get("lm_id", ""),
                            "uid": props.get("uid", ""),
                            "is_temporarily_closed": props.get("closed", False),
                        }
                    }

            elif cat == "area" and cls == "building" and typ == "section":
                if gid not in sections or geom_area(geo) > geom_area(sections[gid]["geometry"]):
                    sections[gid] = {
                        "type": "Feature",
                        "geometry": geo,
                        "properties": {
                            "geom_id": gid, "name": props.get("name", ""),
                            "floor_id": props.get("floor_id", ""),
                            "floor_name": props.get("floor_name", ""),
                            "floor_level": props.get("floor_level", ""),
                        }
                    }

            elif cat == "room" and cls != "tourism":
                if gid not in other_rooms or geom_area(geo) > geom_area(other_rooms[gid]["geometry"]):
                    other_rooms[gid] = {
                        "type": "Feature",
                        "geometry": geo,
                        "properties": {
                            "geom_id": gid, "name": props.get("name", ""),
                            "class": cls, "type": typ,
                            "floor_id": props.get("floor_id", ""),
                            "floor_name": props.get("floor_name", ""),
                            "floor_level": props.get("floor_level", ""),
                        }
                    }

    return galleries, sections, other_rooms

def main():
    center_lat, center_lng = 40.779448, -73.963517

    # Extract at zoom 15 first (large tiles, no clipping for big rooms)
    print("=== Extracting at zoom 15 ===")
    z15_x, z15_y = lat_lng_to_tile(center_lat, center_lng, 15)
    z15_tiles = [(z15_x + dx, z15_y + dy) for dx in range(-1, 2) for dy in range(-1, 2)]
    g15, s15, o15 = extract_from_tiles(15, z15_tiles)
    print(f"  z15: {len(g15)} galleries, {len(s15)} sections, {len(o15)} other")

    # Also extract at zoom 16
    print("\n=== Extracting at zoom 16 ===")
    z16_x, z16_y = lat_lng_to_tile(center_lat, center_lng, 16)
    z16_tiles = [(z16_x + dx, z16_y + dy) for dx in range(-1, 2) for dy in range(-1, 2)]
    g16, s16, o16 = extract_from_tiles(16, z16_tiles)
    print(f"  z16: {len(g16)} galleries, {len(s16)} sections, {len(o16)} other")

    # Also extract at zoom 17 for any small rooms missed at lower zoom
    print("\n=== Extracting at zoom 17 ===")
    z17_x, z17_y = lat_lng_to_tile(center_lat, center_lng, 17)
    z17_tiles = [(z17_x + dx, z17_y + dy) for dx in range(-1, 2) for dy in range(-1, 2)]
    g17, s17, o17 = extract_from_tiles(17, z17_tiles)
    print(f"  z17: {len(g17)} galleries, {len(s17)} sections, {len(o17)} other")

    # Use z16 exclusively - best balance of coverage and positional accuracy.
    # z15 has ~400m positional offset due to low coordinate precision.
    # z17 clips rooms at tile boundaries.
    galleries = g16
    sections = s16
    other_rooms = o16

    print(f"\n=== Merged ===")
    print(f"Galleries: {len(galleries)}")
    print(f"Sections: {len(sections)}")
    print(f"Other rooms: {len(other_rooms)}")

    # Check gallery 207 specifically
    for gid, feat in galleries.items():
        if feat["properties"]["gallery_number"] == "207":
            v = count_vertices(feat["geometry"])
            coords = feat["geometry"]["coordinates"][0] if feat["geometry"]["type"] == "Polygon" else feat["geometry"]["coordinates"][0][0]
            lngs = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            w = (max(lngs) - min(lngs)) * 111000 * 0.7
            h = (max(lats) - min(lats)) * 111000
            print(f"\nGallery 207: {v} vertices, ~{w:.0f}m x {h:.0f}m")
            break

    # By floor
    floors = {}
    for feat in galleries.values():
        fl = feat["properties"]["floor_name"]
        floors[fl] = floors.get(fl, 0) + 1
    print("\nGalleries by floor:")
    for fl, ct in sorted(floors.items()):
        print(f"  {fl}: {ct}")

    # Save
    def save_geojson(data, path):
        gj = {"type": "FeatureCollection", "features": list(data.values())}
        with open(path, "w") as f:
            json.dump(gj, f)
        print(f"Saved {path} ({len(gj['features'])} features)")

    save_geojson(galleries, "data/gallery_rooms.geojson")
    save_geojson(sections, "data/section_areas.geojson")
    save_geojson(other_rooms, "data/other_rooms.geojson")

    # Also re-extract floor outlines
    floor_polys = {gid: f for gid, f in other_rooms.items() if f["properties"].get("type") == "floor"}
    save_geojson(floor_polys, "data/floor_outlines.geojson")

if __name__ == "__main__":
    main()
