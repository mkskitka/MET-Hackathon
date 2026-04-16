#!/usr/bin/env python3
"""
Extract door positions from vector tiles and match each door to the two rooms it connects.
Outputs data/room_doors.json with door midpoints indexed by room pair.
"""

import json
import math
import mapbox_vector_tile
import urllib.request

TILE_URL = "https://prod.cdn.livingmap.com/tiles/the_met/{z}/{x}/{y}.pbf?lang=en-GB"
CENTER_LNG = -73.963517  # for mirroring

def pixel_to_latlng(px, py, tx, ty, z, ext=4096):
    n = 2 ** z
    lng = (tx + px / ext) / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + py / ext) / n))))
    return lat, lng

def convert_line(coords, tx, ty, z, ext):
    result = []
    for c in coords:
        lat, lng = pixel_to_latlng(c[0], c[1], tx, ty, z, ext)
        # Mirror lng to match our flipped map
        lng = 2 * CENTER_LNG - lng
        result.append([lng, lat])
    return result

def line_midpoint(coords):
    if len(coords) < 2:
        return coords[0] if coords else None
    total = 0
    for i in range(len(coords) - 1):
        dx = coords[i+1][0] - coords[i][0]
        dy = coords[i+1][1] - coords[i][1]
        total += math.sqrt(dx*dx + dy*dy)
    half = total / 2
    running = 0
    for i in range(len(coords) - 1):
        dx = coords[i+1][0] - coords[i][0]
        dy = coords[i+1][1] - coords[i][1]
        seg = math.sqrt(dx*dx + dy*dy)
        if running + seg >= half and seg > 0:
            t = (half - running) / seg
            return [coords[i][0] + t * dx, coords[i][1] + t * dy]
        running += seg
    return coords[-1]

def point_in_polygon(px, py, polygon):
    ring = polygon[0]
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

def fetch_tile(z, x, y):
    url = TILE_URL.format(z=z, x=x, y=y)
    req = urllib.request.Request(url)
    req.add_header("Referer", "https://maps.metmuseum.org/")
    with urllib.request.urlopen(req) as resp:
        return mapbox_vector_tile.decode(resp.read())

def main():
    zoom = 16
    center_lat, center_lng = 40.779448, -73.963517
    n = 2 ** zoom
    cx = int((center_lng + 180.0) / 360.0 * n)
    lat_rad = math.radians(center_lat)
    cy = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    tiles = [(cx + dx, cy + dy) for dx in range(-1, 2) for dy in range(-1, 2)]

    # Collect galleries and doors from tiles
    all_galleries = {}  # geom_id -> {num, floor, polygons (mirrored)}
    all_doors = []  # {midpoint, floor, line_coords}

    for tx, ty in tiles:
        print(f"Processing tile {zoom}/{tx}/{ty}...")
        try:
            decoded = fetch_tile(zoom, tx, ty)
        except:
            continue
        indoor = decoded.get("indoor", {})
        features = indoor.get("features", [])
        ext = indoor.get("extent", 4096)

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            geom_type = geom.get("type", "")
            cat = props.get("category", "")
            typ = props.get("type", "")
            gid = props.get("geom_id", 0)
            floor = props.get("floor_name", "")

            if cat == "room" and props.get("class") == "tourism" and typ == "gallery" and geom_type in ("Polygon", "MultiPolygon"):
                if gid not in all_galleries:
                    coords = geom["coordinates"]
                    if geom_type == "Polygon":
                        mirrored = [[[2*CENTER_LNG - pixel_to_latlng(c[0], c[1], tx, ty, zoom, ext)[1], pixel_to_latlng(c[0], c[1], tx, ty, zoom, ext)[0]] for c in ring] for ring in coords]
                        # Fix: convert properly
                        mirrored = []
                        for ring in coords:
                            new_ring = []
                            for c in ring:
                                lat, lng = pixel_to_latlng(c[0], c[1], tx, ty, zoom, ext)
                                lng = 2 * CENTER_LNG - lng
                                new_ring.append([lng, lat])
                            mirrored.append(new_ring)
                        polys = [mirrored]
                    else:
                        polys = []
                        for poly in coords:
                            new_poly = []
                            for ring in poly:
                                new_ring = []
                                for c in ring:
                                    lat, lng = pixel_to_latlng(c[0], c[1], tx, ty, zoom, ext)
                                    lng = 2 * CENTER_LNG - lng
                                    new_ring.append([lng, lat])
                                new_poly.append(new_ring)
                            polys.append(new_poly)
                    all_galleries[gid] = {
                        "num": props.get("name", ""),
                        "floor": floor,
                        "polys": polys,
                    }

            if cat == "barrier" and typ == "door" and geom_type == "LineString":
                line = convert_line(geom["coordinates"], tx, ty, zoom, ext)
                mid = line_midpoint(line)
                if mid:
                    all_doors.append({"midpoint": mid, "floor": floor, "line": line})

    print(f"\nGalleries: {len(all_galleries)}, Doors: {len(all_doors)}")

    # Index galleries by floor
    gals_by_floor = {}
    for gid, g in all_galleries.items():
        fl = g["floor"]
        if fl not in gals_by_floor:
            gals_by_floor[fl] = []
        gals_by_floor[fl].append(g)

    # For each door, find which two galleries it sits between
    EPSILON = 0.00002
    door_connections = {}  # "roomA-roomB" -> [door_midpoints]

    for door in all_doors:
        mx, my = door["midpoint"]
        fl = door["floor"]
        if fl not in gals_by_floor:
            continue

        test_points = [
            (mx + EPSILON, my), (mx - EPSILON, my),
            (mx, my + EPSILON), (mx, my - EPSILON),
            (mx + EPSILON, my + EPSILON), (mx - EPSILON, my - EPSILON),
            (mx + EPSILON, my - EPSILON), (mx - EPSILON, my + EPSILON),
        ]

        touching = set()
        for g in gals_by_floor[fl]:
            for poly in g["polys"]:
                for tp in test_points:
                    if point_in_polygon(tp[0], tp[1], poly):
                        touching.add(g["num"])
                        break

        if len(touching) >= 2:
            nums = sorted(touching)
            for i in range(len(nums)):
                for j in range(i + 1, len(nums)):
                    key = f"{nums[i]}-{nums[j]}"
                    if key not in door_connections:
                        door_connections[key] = []
                    door_connections[key].append({
                        "lng": door["midpoint"][0],
                        "lat": door["midpoint"][1],
                        "floor": fl,
                    })

    print(f"Door connections: {len(door_connections)} room pairs with doors")

    # Build output: for each room pair, pick the door closest to the line between centroids
    # Also build a centroid lookup
    centroids = {}
    for gid, g in all_galleries.items():
        ring = g["polys"][0][0]
        n = len(ring) - 1
        if n > 0:
            cx = sum(p[0] for p in ring[:n]) / n
            cy = sum(p[1] for p in ring[:n]) / n
            centroids[g["num"]] = [cx, cy]

    output = {}
    for key, doors in door_connections.items():
        a, b = key.split("-")
        # Use the first door (or average if multiple)
        if len(doors) == 1:
            d = doors[0]
        else:
            d = {
                "lng": sum(dd["lng"] for dd in doors) / len(doors),
                "lat": sum(dd["lat"] for dd in doors) / len(doors),
                "floor": doors[0]["floor"],
            }
        output[key] = d

    with open("data/room_doors.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved data/room_doors.json ({len(output)} door positions)")

    # Show samples
    for key in sorted(output.keys())[:15]:
        d = output[key]
        print(f"  {key}: [{d['lng']:.6f}, {d['lat']:.6f}] ({d['floor']})")

if __name__ == "__main__":
    main()
