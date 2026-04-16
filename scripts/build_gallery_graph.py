#!/usr/bin/env python3
"""
Build a gallery connectivity graph for the Asian Art wing.
Uses manually-defined adjacency based on the actual floor plan
(which rooms have doors connecting them).

Output: data/gallery_graph.json
"""

import json
import pandas as pd

def load_gallery_positions():
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

    # Interpolated positions for galleries missing from the API
    interpolated = {
        207: {"lat": 40.779450, "lng": -73.962850, "name": "Chinese Art: Ancient to Tang Dynasty"},
        209: {"lat": 40.779850, "lng": -73.962400, "name": "Chinese Buddhist Art"},
        211: {"lat": 40.780100, "lng": -73.962350, "name": "Chinese Painting"},
        212: {"lat": 40.780150, "lng": -73.962250, "name": "Chinese Painting"},
        213: {"lat": 40.780100, "lng": -73.962050, "name": "Chinese Painting"},
        219: {"lat": 40.779350, "lng": -73.962550, "name": "Chinese Jade & Decorative Arts"},
        220: {"lat": 40.779500, "lng": -73.962500, "name": "Chinese Decorative Arts"},
        221: {"lat": 40.779550, "lng": -73.962400, "name": "Chinese Decorative Arts"},
        222: {"lat": 40.779350, "lng": -73.962400, "name": "Chinese Jade Collection"},
        251: {"lat": 40.780150, "lng": -73.961850, "name": "Southeast Asian Art"},
    }
    for gnum, data in interpolated.items():
        if gnum not in positions:
            positions[gnum] = data

    return positions


# Physical room-to-room connections based on the Met floor plan.
# Each entry means there is a doorway between the two rooms.
PHYSICAL_ADJACENCY = {
    # Chinese Ceramics cluster (entrance area)
    200: [201, 202],
    201: [200],
    202: [200, 203, 204, 207],
    203: [202, 204],
    204: [202, 203, 205, 234],
    205: [204, 206],
    206: [205, 207],

    # Ancient Chinese / large central gallery
    207: [202, 206, 208, 219, 220],

    # Chinese Buddhist
    208: [207, 209, 233],
    209: [208, 239],

    # Chinese Painting + Garden (right side)
    210: [211, 217, 232],
    211: [210, 212],
    212: [211, 213],
    213: [212, 214],
    214: [213, 215],
    215: [214, 216, 246],
    216: [215, 217, 244, 253],
    217: [210, 216, 218],  # Chinese Garden
    218: [217, 213],

    # Chinese Jade & Decorative Arts
    219: [207, 220, 222],
    220: [207, 219, 221],
    221: [220, 222],
    222: [219, 221],

    # Japanese wing (loop)
    223: [224, 232],
    224: [223, 225, 231],
    225: [224, 226, 230],
    226: [225, 227, 229],
    227: [226, 228],
    228: [227, 229],
    229: [226, 228, 230],
    230: [225, 229, 231],
    231: [224, 230, 232],
    232: [210, 223, 231],

    # Korean
    233: [208, 234, 235],

    # South Asian (corridor of rooms)
    234: [204, 233, 235],
    235: [233, 234, 236],
    236: [235, 237],
    237: [236, 238],
    238: [237, 239],
    239: [209, 238, 240, 241],

    # South Asian (lower rooms)
    240: [239, 241],
    241: [239, 240, 242, 243, 244],
    242: [241, 243],
    243: [241, 242, 244],

    # Southeast Asian
    244: [216, 241, 243, 245, 247],
    245: [244, 246, 247, 252, 253],
    246: [215, 245, 248],
    247: [244, 245, 252],
    248: [246, 249],
    249: [248, 250],
    250: [249],

    # Himalayan
    251: [250, 249],
    252: [245, 247, 253],
    253: [216, 245, 252],
}


def define_regions():
    return {
        "chinese_ceramics": {
            "name": "Chinese Ceramics",
            "galleries": [200, 201, 202, 203, 204, 205],
        },
        "chinese_ancient": {
            "name": "Ancient China",
            "galleries": [207, 219, 220, 221, 222],
        },
        "chinese_buddhist": {
            "name": "Chinese Buddhist Art",
            "galleries": [206, 208, 209],
        },
        "chinese_painting": {
            "name": "Chinese Paintings & Garden",
            "galleries": [210, 211, 212, 213, 214, 215, 216, 217, 218],
        },
        "japanese": {
            "name": "Japanese Art",
            "galleries": [223, 224, 225, 226, 227, 228, 229, 230, 231, 232],
        },
        "korean": {
            "name": "Korean Art",
            "galleries": [233],
        },
        "south_asian": {
            "name": "South Asian Art",
            "galleries": [234, 235, 236, 237, 238, 239, 240, 241, 242, 243],
        },
        "southeast_asian": {
            "name": "Southeast Asian Art",
            "galleries": [244, 245, 246, 247, 248, 249, 250, 251],
        },
        "himalayan": {
            "name": "Himalayan Art",
            "galleries": [252, 253],
        },
    }


def find_shortest_path(start, end):
    """BFS shortest path using physical adjacency only."""
    if start == end:
        return [start]
    visited = {start}
    queue = [[start]]
    while queue:
        path = queue.pop(0)
        current = path[-1]
        for neighbor in PHYSICAL_ADJACENCY.get(current, []):
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None


def build_walking_route(target_galleries, start=200):
    """
    Build a walking route that follows physical connections.
    Uses nearest-neighbor but only through connected rooms,
    so the path always goes through doorways.
    """
    remaining = set(target_galleries)
    route = []
    current = start

    if current in remaining:
        remaining.remove(current)
    route.append(current)

    while remaining:
        # Find the target that requires the fewest rooms to reach
        best_target = None
        best_path = None
        best_len = float("inf")

        for target in remaining:
            path = find_shortest_path(current, target)
            if path and len(path) < best_len:
                best_len = len(path)
                best_target = target
                best_path = path

        if best_target is None:
            break

        # Add intermediate rooms (pass-through)
        for g in best_path[1:]:
            route.append(g)

        remaining.remove(best_target)
        current = best_target

    return route


def main():
    positions = load_gallery_positions()
    regions = define_regions()

    # Load artwork stats
    meta = pd.read_csv("data/asian_art_on_view.csv")
    aug = pd.read_csv("data/augmented_fields.csv")
    merged = meta.merge(aug, on="object_id", how="left")

    # Build gallery graph
    graph = {"galleries": {}, "regions": regions, "adjacency_type": "physical_doorways"}

    for gnum in sorted(PHYSICAL_ADJACENCY.keys()):
        pos = positions.get(gnum, {"lat": None, "lng": None, "name": f"Gallery {gnum}"})
        g_data = merged[merged.gallery_number == gnum]
        highlights = g_data[g_data.is_highlight == True]

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
            "neighbors": PHYSICAL_ADJACENCY[gnum],
            "object_count": len(g_data),
            "highlight_count": len(highlights),
            "top_classifications": g_data.classification.value_counts().head(3).to_dict() if len(g_data) > 0 else {},
        }

    # Test routes
    print("=== EXAMPLE ROUTES (physical adjacency) ===\n")

    # Quick route
    targets_30 = [200, 207, 217, 235, 247, 252]
    route_30 = build_walking_route(targets_30, start=200)
    print(f"30-min route: {' → '.join(str(g) for g in route_30)}")
    print(f"  Targets: {sorted(targets_30)}")
    print(f"  Total rooms walked through: {len(route_30)}")
    print()

    # 1-hour route
    targets_60 = [200, 207, 217, 231, 233, 234, 244, 247, 252]
    route_60 = build_walking_route(targets_60, start=200)
    print(f"1-hour route: {' → '.join(str(g) for g in route_60)}")
    print(f"  Targets: {sorted(targets_60)}")
    print(f"  Total rooms walked through: {len(route_60)}")
    print()

    # Verify no jumps — each consecutive pair should be physically adjacent
    for route_name, route in [("30min", route_30), ("60min", route_60)]:
        jumps = []
        for i in range(len(route) - 1):
            a, b = route[i], route[i + 1]
            if b not in PHYSICAL_ADJACENCY.get(a, []):
                jumps.append((a, b))
        if jumps:
            print(f"  WARNING {route_name}: non-adjacent jumps: {jumps}")
        else:
            print(f"  ✓ {route_name}: all transitions are through doorways")

    with open("data/gallery_graph.json", "w") as f:
        json.dump(graph, f, indent=2)

    total_edges = sum(len(v) for v in PHYSICAL_ADJACENCY.values()) // 2
    print(f"\nSaved data/gallery_graph.json")
    print(f"  {len(graph['galleries'])} galleries, {total_edges} physical connections")


if __name__ == "__main__":
    main()
