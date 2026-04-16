#!/usr/bin/env python3
"""
Build a complete gallery graph for routing through the Asian Art wing.
Outputs: data/gallery_graph.json

Includes:
- All gallery positions (real + interpolated for missing ones)
- Adjacency with walking distances
- Named regions/clusters
- Path-finding functions
"""

import json
import math
import pandas as pd
from collections import defaultdict

def load_gallery_positions():
    """Load known positions and interpolate missing ones."""
    with open("data/all_galleries.json") as f:
        gals = json.load(f)

    positions = {}
    for g in gals:
        gnum = g.get("gallery_number", "")
        if gnum.isdigit() and 200 <= int(gnum) <= 253:
            positions[int(gnum)] = {
                "lat": g["center_lat"],
                "lng": g["center_lng"],
                "name": g.get("long_name", f"Gallery {gnum}"),
            }

    # Interpolate missing galleries based on known neighbors
    # These are approximate positions based on the Met floor plan
    interpolated = {
        207: {"lat": 40.779450, "lng": -73.962850, "name": "Chinese Art: Ancient to Tang Dynasty"},
        209: {"lat": 40.779850, "lng": -73.962400, "name": "Chinese Buddhist Art"},
        211: {"lat": 40.780100, "lng": -73.962350, "name": "Chinese Painting"},
        212: {"lat": 40.780050, "lng": -73.962300, "name": "Chinese Painting"},
        213: {"lat": 40.780150, "lng": -73.962150, "name": "Chinese Painting"},
        219: {"lat": 40.779350, "lng": -73.962550, "name": "Chinese Jade & Decorative Arts"},
        220: {"lat": 40.779450, "lng": -73.962450, "name": "Chinese Decorative Arts"},
        221: {"lat": 40.779550, "lng": -73.962350, "name": "Chinese Decorative Arts"},
        222: {"lat": 40.779350, "lng": -73.962400, "name": "Chinese Jade Collection"},
        251: {"lat": 40.780150, "lng": -73.961850, "name": "Southeast Asian Art"},
    }

    for gnum, data in interpolated.items():
        if gnum not in positions:
            positions[gnum] = data

    return positions


def distance_meters(pos1, pos2):
    """Approximate distance in meters between two lat/lng points."""
    dlat = (pos1["lat"] - pos2["lat"]) * 111000
    dlng = (pos1["lng"] - pos2["lng"]) * 85000  # NYC latitude
    return math.sqrt(dlat**2 + dlng**2)


def build_adjacency(positions, max_distance=40):
    """Build adjacency graph. Galleries within max_distance meters are connected."""
    adjacency = defaultdict(list)

    nums = sorted(positions.keys())
    for i, a in enumerate(nums):
        for b in nums[i+1:]:
            d = distance_meters(positions[a], positions[b])
            if d < max_distance:
                adjacency[a].append({"gallery": b, "distance": round(d, 1)})
                adjacency[b].append({"gallery": a, "distance": round(d, 1)})

    # Sort neighbors by distance
    for k in adjacency:
        adjacency[k].sort(key=lambda x: x["distance"])

    return dict(adjacency)


def define_regions():
    """Group galleries into named regions for route descriptions."""
    return {
        "chinese_ceramics": {
            "name": "Chinese Ceramics",
            "galleries": [200, 201, 202, 203, 204, 205],
            "description": "Porcelain and ceramics spanning dynastic China",
        },
        "chinese_ancient": {
            "name": "Ancient China",
            "galleries": [207, 219, 220, 221, 222],
            "description": "Bronze age through Tang dynasty — jade, metalwork, and ancient art",
        },
        "chinese_buddhist": {
            "name": "Chinese Buddhist Art",
            "galleries": [206, 208, 209],
            "description": "Buddhist sculpture and painting from China",
        },
        "chinese_painting": {
            "name": "Chinese Paintings",
            "galleries": [210, 211, 212, 213, 214, 215, 216],
            "description": "Painting and calligraphy across the dynasties",
        },
        "chinese_garden": {
            "name": "Chinese Garden (Astor Court)",
            "galleries": [217, 218],
            "description": "A full-scale Ming dynasty courtyard — a must-see peaceful oasis",
        },
        "japanese": {
            "name": "Japanese Art",
            "galleries": [223, 224, 225, 226, 227, 228, 229, 230, 231, 232],
            "description": "Ceramics, screens, prints, and paintings from Japan",
        },
        "korean": {
            "name": "Korean Art",
            "galleries": [233],
            "description": "Ceramics, metalwork, and painting from Korea",
        },
        "south_asian": {
            "name": "South Asian Art",
            "galleries": [234, 235, 236, 237, 238, 239, 240, 241, 242, 243],
            "description": "Hindu, Buddhist, and Jain sculpture from India and beyond",
        },
        "southeast_asian": {
            "name": "Southeast Asian Art",
            "galleries": [244, 245, 246, 247, 248, 249, 250, 251],
            "description": "Sculpture and bronzes from Thailand, Cambodia, Indonesia",
        },
        "himalayan": {
            "name": "Himalayan Art",
            "galleries": [252, 253],
            "description": "Buddhist art from Tibet and Nepal",
        },
    }


def find_shortest_path(adjacency, start, end):
    """BFS shortest path between two galleries."""
    if start == end:
        return [start]

    visited = {start}
    queue = [[start]]

    while queue:
        path = queue.pop(0)
        current = path[-1]

        for neighbor in adjacency.get(current, []):
            n = neighbor["gallery"]
            if n == end:
                return path + [n]
            if n not in visited:
                visited.add(n)
                queue.append(path + [n])

    return None  # No path found


def build_route(adjacency, target_galleries, start=200):
    """
    Build a walking route through target galleries using nearest-neighbor.
    Returns ordered list of galleries to visit (including pass-through galleries).
    """
    if not target_galleries:
        return []

    remaining = set(target_galleries)
    route = []
    current = start

    # If start is a target, visit it
    if current in remaining:
        remaining.remove(current)
    route.append(current)

    while remaining:
        # Find nearest unvisited target
        best = None
        best_dist = float("inf")
        best_path = None

        for target in remaining:
            path = find_shortest_path(adjacency, current, target)
            if path:
                dist = len(path)
                if dist < best_dist:
                    best_dist = dist
                    best = target
                    best_path = path

        if best is None:
            break

        # Add the path (excluding current which is already in route)
        for g in best_path[1:]:
            if g not in route:
                route.append(g)

        remaining.remove(best)
        current = best

    return route


def main():
    positions = load_gallery_positions()
    adjacency_raw = build_adjacency(positions)
    regions = define_regions()

    # Convert adjacency to simpler format for path finding
    adj_simple = {}
    for k, neighbors in adjacency_raw.items():
        adj_simple[k] = neighbors

    # Load artwork data for gallery stats
    meta = pd.read_csv("data/asian_art_on_view.csv")
    aug = pd.read_csv("data/augmented_fields.csv")
    merged = meta.merge(aug, on="object_id", how="left")

    # Build gallery stats
    gallery_stats = {}
    for gnum in sorted(positions.keys()):
        g_data = merged[merged.gallery_number == gnum]
        highlights = g_data[g_data.is_highlight == True]

        gallery_stats[gnum] = {
            "object_count": len(g_data),
            "highlight_count": len(highlights),
            "top_classifications": g_data.classification.value_counts().head(3).to_dict() if len(g_data) > 0 else {},
            "top_culture": g_data.culture.value_counts().index[0] if len(g_data) > 0 else "",
        }

    # Build the full graph
    graph = {
        "galleries": {},
        "regions": regions,
    }

    for gnum, pos in sorted(positions.items()):
        neighbors = adjacency_raw.get(gnum, [])
        stats = gallery_stats.get(gnum, {})

        # Find which region this gallery belongs to
        region = None
        for rkey, rdata in regions.items():
            if gnum in rdata["galleries"]:
                region = rkey
                break

        graph["galleries"][str(gnum)] = {
            "number": gnum,
            "name": pos["name"],
            "lat": pos["lat"],
            "lng": pos["lng"],
            "region": region,
            "neighbors": [n["gallery"] for n in neighbors],
            "neighbor_distances": {n["gallery"]: n["distance"] for n in neighbors},
            "object_count": stats.get("object_count", 0),
            "highlight_count": stats.get("highlight_count", 0),
            "top_classifications": stats.get("top_classifications", {}),
            "top_culture": stats.get("top_culture", ""),
        }

    # Generate example routes
    print("=== EXAMPLE ROUTES ===\n")

    # Route 1: Quick 30-min highlights
    highlight_galleries = [g for g, s in gallery_stats.items()
                          if s["highlight_count"] >= 3 and g <= 253]
    highlight_galleries.sort(key=lambda g: -gallery_stats[g]["highlight_count"])
    top_6 = highlight_galleries[:6]
    # Always include Chinese Garden
    if 217 not in top_6:
        top_6[-1] = 217

    route_30 = build_route(adj_simple, top_6, start=200)
    print(f"30-min highlights ({len(route_30)} galleries):")
    for g in route_30:
        name = positions.get(g, {}).get("name", "?")
        count = gallery_stats.get(g, {}).get("object_count", 0)
        hl = gallery_stats.get(g, {}).get("highlight_count", 0)
        is_target = "★" if g in top_6 else "→"
        print(f"  {is_target} Gallery {g}: {name} ({count} objects, {hl} highlights)")

    print()

    # Route 2: 1-hour cultural tour
    cultural_stops = [200, 207, 217, 231, 233, 234, 244, 247, 252]
    route_60 = build_route(adj_simple, cultural_stops, start=200)
    print(f"1-hour cultural tour ({len(route_60)} galleries):")
    for g in route_60:
        name = positions.get(g, {}).get("name", "?")
        count = gallery_stats.get(g, {}).get("object_count", 0)
        is_target = "★" if g in cultural_stops else "→"
        print(f"  {is_target} Gallery {g}: {name} ({count} objects)")

    print()

    # Route 3: Full 2-hour tour
    all_regions_stops = []
    for rkey, rdata in regions.items():
        # Pick 1-2 galleries per region
        region_gals = [g for g in rdata["galleries"] if g in gallery_stats]
        region_gals.sort(key=lambda g: -gallery_stats.get(g, {}).get("highlight_count", 0))
        all_regions_stops.extend(region_gals[:2])
    if 217 not in all_regions_stops:
        all_regions_stops.append(217)
    route_120 = build_route(adj_simple, all_regions_stops, start=200)
    print(f"2-hour full tour ({len(route_120)} galleries):")
    for g in route_120:
        name = positions.get(g, {}).get("name", "?")
        count = gallery_stats.get(g, {}).get("object_count", 0)
        is_target = "★" if g in all_regions_stops else "→"
        print(f"  {is_target} Gallery {g}: {name} ({count} objects)")

    # Save the graph
    with open("data/gallery_graph.json", "w") as f:
        json.dump(graph, f, indent=2)

    print(f"\nSaved data/gallery_graph.json")
    print(f"  {len(graph['galleries'])} galleries")
    print(f"  {len(graph['regions'])} regions")
    total_edges = sum(len(g["neighbors"]) for g in graph["galleries"].values()) // 2
    print(f"  {total_edges} connections")


if __name__ == "__main__":
    main()
