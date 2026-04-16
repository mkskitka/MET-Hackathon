#!/usr/bin/env python3
"""
Build room adjacency graph from door positions and room polygons.
A door LineString sits on the boundary between two rooms - we find which rooms
each door touches to determine connectivity.
"""

import json
import math
import mapbox_vector_tile
import urllib.request

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

def point_in_polygon(px, py, polygon):
    """Ray casting algorithm for point-in-polygon test."""
    ring = polygon[0]  # outer ring
    n = len(ring)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def line_midpoint(coords):
    """Get midpoint of a linestring."""
    if len(coords) == 0:
        return None
    if len(coords) == 1:
        return coords[0]
    # Use actual midpoint of first segment
    total_len = 0
    for i in range(len(coords) - 1):
        dx = coords[i+1][0] - coords[i][0]
        dy = coords[i+1][1] - coords[i][1]
        total_len += math.sqrt(dx*dx + dy*dy)

    half = total_len / 2
    running = 0
    for i in range(len(coords) - 1):
        dx = coords[i+1][0] - coords[i][0]
        dy = coords[i+1][1] - coords[i][1]
        seg_len = math.sqrt(dx*dx + dy*dy)
        if running + seg_len >= half:
            t = (half - running) / seg_len if seg_len > 0 else 0
            return [coords[i][0] + t * dx, coords[i][1] + t * dy]
        running += seg_len
    return coords[-1]

def fetch_tile(z, x, y):
    url = TILE_URL.format(z=z, x=x, y=y)
    req = urllib.request.Request(url)
    req.add_header("Referer", "https://maps.metmuseum.org/")
    with urllib.request.urlopen(req) as resp:
        return mapbox_vector_tile.decode(resp.read())

def main():
    zoom = 15
    # Tile range covering the Met at z15
    center_lat, center_lng = 40.779448, -73.963517
    n = 2 ** zoom
    cx = int((center_lng + 180.0) / 360.0 * n)
    lat_rad = math.radians(center_lat)
    cy = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    tiles = [(cx + dx, cy + dy) for dx in range(-1, 2) for dy in range(-1, 2)]

    all_galleries = {}  # geom_id -> {num, floor, polygon_coords}
    all_doors = []  # [{midpoint, floor, geom}]
    all_corridors = {}  # geom_id -> {floor, polygon_coords}

    for tx, ty in tiles:
        print(f"Processing tile {zoom}/{tx}/{ty}...")
        decoded = fetch_tile(zoom, tx, ty)
        if not decoded:
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
            floor = props.get("floor_name", "")

            # Gallery polygons
            if cat == "room" and cls == "tourism" and typ == "gallery" and geom_type in ("Polygon", "MultiPolygon"):
                if gid not in all_galleries:
                    geo = convert_geometry(geom, tx, ty, zoom, extent)
                    all_galleries[gid] = {
                        "num": props.get("name", ""),
                        "floor": floor,
                        "geometry": geo,
                    }

            # Corridor polygons (rooms can connect through corridors)
            if cat == "room" and cls == "building" and typ == "corridor" and geom_type in ("Polygon", "MultiPolygon"):
                if gid not in all_corridors:
                    geo = convert_geometry(geom, tx, ty, zoom, extent)
                    all_corridors[gid] = {"floor": floor, "geometry": geo}

            # Door linestrings
            if cat == "barrier" and typ == "door" and geom_type == "LineString":
                geo = convert_geometry(geom, tx, ty, zoom, extent)
                mid = line_midpoint(geo["coordinates"])
                if mid:
                    all_doors.append({"midpoint": mid, "floor": floor, "geometry": geo})

    print(f"\nGalleries: {len(all_galleries)}")
    print(f"Corridors: {len(all_corridors)}")
    print(f"Doors: {len(all_doors)}")

    # For each door, find which galleries it connects
    # Expand the door midpoint slightly in all directions and check containment
    EPSILON = 0.00002  # ~2m at this latitude

    edges = set()
    gallery_by_floor = {}
    for gid, g in all_galleries.items():
        fl = g["floor"]
        if fl not in gallery_by_floor:
            gallery_by_floor[fl] = []
        gallery_by_floor[fl].append(g)

    for door in all_doors:
        mx, my = door["midpoint"]
        fl = door["floor"]
        if fl not in gallery_by_floor:
            continue

        # Test points around the door midpoint
        test_points = [
            (mx + EPSILON, my),
            (mx - EPSILON, my),
            (mx, my + EPSILON),
            (mx, my - EPSILON),
            (mx + EPSILON, my + EPSILON),
            (mx - EPSILON, my - EPSILON),
            (mx + EPSILON, my - EPSILON),
            (mx - EPSILON, my + EPSILON),
        ]

        touching = set()
        for g in gallery_by_floor[fl]:
            coords = g["geometry"]["coordinates"]
            polys = coords if g["geometry"]["type"] == "MultiPolygon" else [coords]
            for poly in polys:
                for tp in test_points:
                    if point_in_polygon(tp[0], tp[1], poly):
                        touching.add(g["num"])
                        break

        if len(touching) >= 2:
            nums = sorted(touching)
            for i in range(len(nums)):
                for j in range(i + 1, len(nums)):
                    edges.add((nums[i], nums[j], fl))

    print(f"\nConnections found: {len(edges)}")

    # Build adjacency list
    adjacency = {}
    for a, b, floor in edges:
        if a not in adjacency:
            adjacency[a] = []
        if b not in adjacency:
            adjacency[b] = []
        adjacency[a].append({"to": b, "floor": floor})
        adjacency[b].append({"to": a, "floor": floor})

    print(f"Galleries with connections: {len(adjacency)}")

    # Show some samples
    for num in sorted(adjacency.keys())[:20]:
        neighbors = [e["to"] for e in adjacency[num]]
        print(f"  Gallery {num} -> {', '.join(neighbors)}")

    # Save
    # Also build GeoJSON lines for visualization
    edge_features = []
    # Build centroid lookup
    centroids = {}
    for gid, g in all_galleries.items():
        coords = g["geometry"]["coordinates"]
        if g["geometry"]["type"] == "Polygon":
            ring = coords[0]
        else:
            ring = coords[0][0]
        n = len(ring) - 1
        if n > 0:
            cx = sum(p[0] for p in ring[:n]) / n
            cy = sum(p[1] for p in ring[:n]) / n
            centroids[g["num"]] = [cx, cy]

    for a, b, floor in edges:
        if a in centroids and b in centroids:
            edge_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [centroids[a], centroids[b]]
                },
                "properties": {"from": a, "to": b, "floor": floor}
            })

    with open("data/room_connections.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": edge_features}, f)

    with open("data/room_adjacency.json", "w") as f:
        json.dump(adjacency, f, indent=2)

    print(f"\nSaved data/room_connections.geojson ({len(edge_features)} edges)")
    print(f"Saved data/room_adjacency.json ({len(adjacency)} galleries)")

if __name__ == "__main__":
    main()
