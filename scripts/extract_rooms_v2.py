#!/usr/bin/env python3
"""
Extract gallery room polygons from Met vector tiles -> GeoJSON.
Uses all available zoom-17 tiles to cover the full museum.
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

def convert_coords(coords, tile_x, tile_y, zoom, extent):
    """Recursively convert coordinate arrays from tile to latlng."""
    if isinstance(coords[0], (int, float)):
        lat, lng = pixel_to_latlng(coords[0], coords[1], tile_x, tile_y, zoom, extent)
        return [lng, lat]
    return [convert_coords(c, tile_x, tile_y, zoom, extent) for c in coords]

def convert_geometry(geom, tile_x, tile_y, zoom, extent=4096):
    return {
        "type": geom["type"],
        "coordinates": convert_coords(geom["coordinates"], tile_x, tile_y, zoom, extent)
    }

def fetch_and_decode_tile(z, x, y):
    url = TILE_URL.format(z=z, x=x, y=y)
    req = urllib.request.Request(url)
    req.add_header("Referer", "https://maps.metmuseum.org/")
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            return mapbox_vector_tile.decode(data)
    except Exception as e:
        print(f"  Failed tile {z}/{x}/{y}: {e}")
        return None

def main():
    zoom = 17
    # The Met Fifth Avenue covers roughly these tile ranges at z17
    # Center is 40.779448, -73.963517 -> tile 38606, 49248
    # Museum extends roughly 500m in each direction
    # At z17, each tile is ~1.2km, so we need a few tiles
    center_lat, center_lng = 40.779448, -73.963517

    # Calculate tile range (museum is roughly 400m x 300m)
    n = 2 ** zoom
    cx = int((center_lng + 180.0) / 360.0 * n)
    lat_rad = math.radians(center_lat)
    cy = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

    # Check adjacent tiles too
    tile_range = [(cx + dx, cy + dy) for dx in range(-1, 2) for dy in range(-1, 2)]

    all_galleries = {}  # keyed by geom_id to deduplicate
    all_sections = {}
    all_other_rooms = {}

    for tx, ty in tile_range:
        print(f"Processing tile {zoom}/{tx}/{ty}...")
        decoded = fetch_and_decode_tile(zoom, tx, ty)
        if not decoded:
            continue

        indoor = decoded.get("indoor", {})
        features = indoor.get("features", [])
        extent = indoor.get("extent", 4096)

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            geom_type = geom.get("type", "")
            category = props.get("category", "")
            cls = props.get("class", "")
            typ = props.get("type", "")
            name = props.get("name", "")
            geom_id = props.get("geom_id", 0)
            offset_id = props.get("offset_id", "")

            # Gallery room polygons
            if category == "room" and cls == "tourism" and typ == "gallery" and geom_type in ("Polygon", "MultiPolygon"):
                if geom_id not in all_galleries:
                    geo_geom = convert_geometry(geom, tx, ty, zoom, extent)
                    all_galleries[geom_id] = {
                        "type": "Feature",
                        "geometry": geo_geom,
                        "properties": {
                            "geom_id": geom_id,
                            "gallery_number": name,
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

            # Section polygons (wings, departments)
            if category == "area" and cls == "building" and typ == "section" and geom_type in ("Polygon", "MultiPolygon"):
                if geom_id not in all_sections:
                    geo_geom = convert_geometry(geom, tx, ty, zoom, extent)
                    all_sections[geom_id] = {
                        "type": "Feature",
                        "geometry": geo_geom,
                        "properties": {
                            "geom_id": geom_id,
                            "name": name,
                            "floor_id": props.get("floor_id", ""),
                            "floor_name": props.get("floor_name", ""),
                            "floor_level": props.get("floor_level", ""),
                        }
                    }

            # Other room types (corridors, exhibitions, etc)
            if category == "room" and geom_type in ("Polygon", "MultiPolygon") and cls != "tourism":
                if geom_id not in all_other_rooms:
                    geo_geom = convert_geometry(geom, tx, ty, zoom, extent)
                    all_other_rooms[geom_id] = {
                        "type": "Feature",
                        "geometry": geo_geom,
                        "properties": {
                            "geom_id": geom_id,
                            "name": name,
                            "class": cls,
                            "type": typ,
                            "floor_id": props.get("floor_id", ""),
                            "floor_name": props.get("floor_name", ""),
                            "floor_level": props.get("floor_level", ""),
                        }
                    }

    # Gallery polygons
    gallery_list = list(all_galleries.values())
    print(f"\n=== Results ===")
    print(f"Gallery room polygons: {len(gallery_list)}")

    # By floor
    floors = {}
    for g in gallery_list:
        fl = g["properties"].get("floor_name", "?")
        floors[fl] = floors.get(fl, 0) + 1
    print("Galleries by floor:")
    for fl, count in sorted(floors.items()):
        print(f"  {fl}: {count}")

    # Save gallery GeoJSON
    gallery_geojson = {"type": "FeatureCollection", "features": gallery_list}
    with open("data/gallery_rooms.geojson", "w") as f:
        json.dump(gallery_geojson, f)
    print(f"\nSaved to data/gallery_rooms.geojson")

    # Save sections
    section_list = list(all_sections.values())
    print(f"\nSection polygons: {len(section_list)}")
    for s in section_list:
        print(f"  [{s['properties']['floor_name']}] {s['properties']['name']}")

    section_geojson = {"type": "FeatureCollection", "features": section_list}
    with open("data/section_areas.geojson", "w") as f:
        json.dump(section_geojson, f)

    # Save other rooms
    other_list = list(all_other_rooms.values())
    print(f"\nOther room polygons: {len(other_list)}")
    other_geojson = {"type": "FeatureCollection", "features": other_list}
    with open("data/other_rooms.geojson", "w") as f:
        json.dump(other_geojson, f)

    # Also create a combined GeoJSON with everything
    combined = gallery_list + section_list + other_list
    combined_geojson = {"type": "FeatureCollection", "features": combined}
    with open("data/met_complete_floorplan.geojson", "w") as f:
        json.dump(combined_geojson, f)
    print(f"\nSaved combined floorplan ({len(combined)} features) to data/met_complete_floorplan.geojson")

    # Print some gallery samples
    print(f"\nSample galleries:")
    for g in sorted(gallery_list, key=lambda x: x["properties"]["gallery_number"])[:20]:
        p = g["properties"]
        coords = g["geometry"]["coordinates"]
        if g["geometry"]["type"] == "Polygon":
            num_points = len(coords[0])
        else:
            num_points = sum(len(ring) for poly in coords for ring in poly)
        print(f"  Gallery {p['gallery_number']:>5} ({p.get('floor_name', '?')}) - {num_points} vertices")

if __name__ == "__main__":
    main()
