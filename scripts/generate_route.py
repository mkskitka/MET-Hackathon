#!/usr/bin/env python3
"""
Generate a personalized route through the Asian Art wing.

Uses physical doorway adjacency so the path always goes through
connected rooms — no jumping across the map.

Usage:
  python3 scripts/generate_route.py [--time 60] [--profile sample]
"""

import json
import math
import pandas as pd
from collections import defaultdict
from itertools import permutations
import argparse


# --- Physical adjacency (from build_gallery_graph.py) ---

PHYSICAL_ADJACENCY = {
    200: [201, 202], 201: [200], 202: [200, 203, 204, 207],
    203: [202, 204], 204: [202, 203, 205, 234], 205: [204, 206],
    206: [205, 207], 207: [202, 206, 208, 219, 220],
    208: [207, 209, 233], 209: [208, 239],
    210: [211, 217, 232], 211: [210, 212], 212: [211, 213],
    213: [212, 214], 214: [213, 215], 215: [214, 216, 246],
    216: [215, 217, 244, 253], 217: [210, 216, 218],
    218: [217, 213],
    219: [207, 220, 222], 220: [207, 219, 221],
    221: [220, 222], 222: [219, 221],
    223: [224, 232], 224: [223, 225, 231],
    225: [224, 226, 230], 226: [225, 227, 229],
    227: [226, 228], 228: [227, 229],
    229: [226, 228, 230], 230: [225, 229, 231],
    231: [224, 230, 232], 232: [210, 223, 231],
    233: [208, 234, 235],
    234: [204, 233, 235], 235: [233, 234, 236],
    236: [235, 237], 237: [236, 238], 238: [237, 239],
    239: [209, 238, 240, 241],
    240: [239, 241], 241: [239, 240, 242, 243, 244],
    242: [241, 243], 243: [241, 242, 244],
    244: [216, 241, 243, 245, 247],
    245: [244, 246, 247, 252, 253],
    246: [215, 245, 248], 247: [244, 245, 252],
    248: [246, 249], 249: [248, 250], 250: [249],
    251: [250, 249], 252: [245, 247, 253], 253: [216, 245, 252],
}


# --- BFS path finding ---

def find_shortest_path(start, end):
    """BFS shortest path using physical adjacency."""
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


def path_cost(start, end):
    """Number of rooms to walk through to get from start to end."""
    path = find_shortest_path(start, end)
    return len(path) - 1 if path else 999


# --- Route ordering ---

def order_targets_optimal(targets, start=200):
    """
    Find the best ordering of target galleries to minimize total rooms walked.
    For small sets (<= 10), try all permutations.
    For larger sets, use nearest-neighbor with 2-opt improvement.
    """
    if len(targets) <= 1:
        return targets

    # Precompute distances between all pairs
    all_points = [start] + list(targets)
    dist_cache = {}
    for a in all_points:
        for b in all_points:
            if a != b:
                dist_cache[(a, b)] = path_cost(a, b)

    target_list = list(targets)

    if len(target_list) <= 8:
        # Brute force best ordering
        best_order = None
        best_cost = float("inf")
        for perm in permutations(target_list):
            cost = dist_cache.get((start, perm[0]), 999)
            for i in range(len(perm) - 1):
                cost += dist_cache.get((perm[i], perm[i + 1]), 999)
            if cost < best_cost:
                best_cost = cost
                best_order = list(perm)
        return best_order

    # Nearest-neighbor for larger sets
    remaining = set(target_list)
    order = []
    current = start
    while remaining:
        best = min(remaining, key=lambda t: dist_cache.get((current, t), 999))
        order.append(best)
        remaining.remove(best)
        current = best

    # 2-opt improvement
    improved = True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 2, len(order)):
                # Try reversing the segment between i and j
                new_order = order[:i] + order[i:j+1][::-1] + order[j+1:]
                old_cost = _route_cost(start, order, dist_cache)
                new_cost = _route_cost(start, new_order, dist_cache)
                if new_cost < old_cost:
                    order = new_order
                    improved = True

    return order


def _route_cost(start, order, dist_cache):
    if not order:
        return 0
    cost = dist_cache.get((start, order[0]), 999)
    for i in range(len(order) - 1):
        cost += dist_cache.get((order[i], order[i + 1]), 999)
    return cost


def build_walking_route(target_galleries, start=200):
    """
    Build an optimal walking route through connected rooms.
    Returns list of ALL rooms to walk through (targets + pass-throughs).
    """
    # Find optimal target ordering
    ordered_targets = order_targets_optimal(target_galleries, start)

    # Build the full path by connecting consecutive targets
    route = [start] if start not in ordered_targets else []
    current = start

    for target in ordered_targets:
        path = find_shortest_path(current, target)
        if path:
            # Skip first element (it's current, already in route)
            for g in path[1:]:
                route.append(g)
            current = target

    # Deduplicate while preserving order (rooms visited twice stay twice — that's backtracking)
    return route


# --- Data loading ---

def load_data():
    meta = pd.read_csv("data/asian_art_on_view.csv")
    aug = pd.read_csv("data/augmented_fields.csv")
    desc = pd.read_csv("data/descriptions.csv")

    merged = meta.merge(aug, on="object_id", how="left")
    hf = desc[desc.is_primary == True][["object_id", "source_image_url", "output_alt_text"]]
    merged = merged.merge(hf, on="object_id", how="left")

    merged["culture_group"] = merged.culture.apply(get_culture_group)
    merged["era"] = merged.object_begin_date.apply(get_era)
    merged["class_group"] = merged.classification.apply(get_class_group)

    with open("data/gallery_graph.json") as f:
        graph = json.load(f)

    return merged, graph


def get_culture_group(c):
    if pd.isna(c): return "other"
    cl = c.lower()
    if any(k in cl for k in ["china", "chinese"]): return "east_asia"
    if "japan" in cl: return "japan"
    if "korea" in cl: return "korea"
    if any(k in cl for k in ["india", "nepal", "sri lanka", "bangladesh", "pakistan"]): return "south_asia"
    if any(k in cl for k in ["thailand", "cambodia", "indonesia", "vietnam", "burma"]): return "southeast_asia"
    if "tibet" in cl: return "himalayan"
    return "other"


def get_era(d):
    if pd.isna(d): return "unknown"
    if d < -200: return "ancient"
    if d < 600: return "classical"
    if d < 1300: return "medieval"
    if d < 1600: return "early_modern"
    if d < 1900: return "late_imperial"
    return "modern"


CLASS_MAP = {
    "Ceramics": "ceramics", "Tomb Pottery": "ceramics", "Glass": "ceramics",
    "Sculpture": "sculpture", "Ivories": "sculpture", "Horn": "sculpture",
    "Metalwork": "metalwork", "Cloisonné": "metalwork", "Enamels": "metalwork",
    "Mirrors": "metalwork", "Jewelry": "metalwork",
    "Jade": "jade", "Hardstone": "jade", "Snuff Bottles": "jade",
    "Paintings": "paintings", "Calligraphy": "paintings",
    "Prints": "prints", "Furniture": "furnishings", "Lacquer": "furnishings",
}

def get_class_group(c):
    if pd.isna(c): return "other"
    return CLASS_MAP.get(c, "other")


# --- Scoring ---

def score_object(obj, profile):
    weights = profile["weights"]
    score = 0.0
    score += weights.get("culture", {}).get(obj["culture_group"], 0.3) * 0.3
    score += weights.get("classification", {}).get(obj["class_group"], 0.3) * 0.3
    score += weights.get("era", {}).get(obj["era"], 0.3) * 0.2
    if obj.get("is_highlight"):
        score += 0.1
    if obj.get("object_id") in profile.get("selected_object_ids", []):
        score += 0.3
    return min(score, 1.0)


def score_gallery(gallery_objects, profile):
    if len(gallery_objects) == 0:
        return 0.0
    scores = [score_object(obj, profile) for _, obj in gallery_objects.iterrows()]
    top_scores = sorted(scores, reverse=True)[:5]
    return sum(top_scores) / len(top_scores)


def select_galleries(merged, profile, num_galleries):
    gallery_scores = {}
    gallery_data = {}

    for gnum in merged.gallery_number.unique():
        if gnum > 253:
            continue
        g_objs = merged[merged.gallery_number == gnum]
        gallery_data[int(gnum)] = g_objs
        gallery_scores[int(gnum)] = score_gallery(g_objs, profile)

    selected = []
    used_cultures = defaultdict(int)
    used_classes = defaultdict(int)

    must_visit = [217]
    if profile.get("preferred_gallery") and profile["preferred_gallery"] in gallery_scores:
        must_visit.append(profile["preferred_gallery"])

    for g in must_visit:
        if g in gallery_scores:
            selected.append(g)
            g_objs = gallery_data.get(g, pd.DataFrame())
            if len(g_objs) > 0:
                top_culture = g_objs.culture_group.mode()
                if len(top_culture) > 0:
                    used_cultures[top_culture.iloc[0]] += 1
                top_class = g_objs.class_group.mode()
                if len(top_class) > 0:
                    used_classes[top_class.iloc[0]] += 1

    while len(selected) < num_galleries:
        best_gallery = None
        best_score = -1

        for gnum, base_score in gallery_scores.items():
            if gnum in selected:
                continue
            if gallery_data.get(gnum) is None or len(gallery_data[gnum]) == 0:
                continue

            g_objs = gallery_data[gnum]
            top_culture = g_objs.culture_group.mode()
            top_class = g_objs.class_group.mode()

            penalty = 0.0
            if len(top_culture) > 0 and used_cultures[top_culture.iloc[0]] >= 2:
                penalty += 0.15 * used_cultures[top_culture.iloc[0]]
            if len(top_class) > 0 and used_classes[top_class.iloc[0]] >= 2:
                penalty += 0.1 * used_classes[top_class.iloc[0]]

            adjusted = base_score - penalty
            if adjusted > best_score:
                best_score = adjusted
                best_gallery = gnum

        if best_gallery is None:
            break

        selected.append(best_gallery)
        g_objs = gallery_data[best_gallery]
        if len(g_objs) > 0:
            top_culture = g_objs.culture_group.mode()
            if len(top_culture) > 0:
                used_cultures[top_culture.iloc[0]] += 1
            top_class = g_objs.class_group.mode()
            if len(top_class) > 0:
                used_classes[top_class.iloc[0]] += 1

    return selected


def pick_artworks_for_gallery(gallery_objects, profile, max_picks=3):
    scored = []
    for _, obj in gallery_objects.iterrows():
        s = score_object(obj, profile)
        scored.append((s, obj))

    scored.sort(key=lambda x: -x[0])

    picks = []
    for i, (s, obj) in enumerate(scored[:max_picks]):
        tag = "affinity" if i == 0 else ("stretch" if i == 1 else "wildcard")
        img = obj.source_image_url if pd.notna(obj.source_image_url) else ""
        picks.append({
            "object_id": int(obj.object_id),
            "title": obj.title.strip(),
            "culture": obj.culture if pd.notna(obj.culture) else "",
            "date": obj.object_date if pd.notna(obj.object_date) else "",
            "classification": obj.classification if pd.notna(obj.classification) else "",
            "medium": obj.medium if pd.notna(obj.medium) else "",
            "alt_text": obj.output_alt_text if pd.notna(obj.output_alt_text) else "",
            "image_url": img.replace("/original/", "/mobile-large/") if img else "",
            "highlight": bool(obj.is_highlight),
            "score": round(s, 3),
            "tag": tag,
        })

    return picks


# --- Main ---

def generate_route(profile):
    merged, graph = load_data()

    time_minutes = profile.get("time_budget_minutes", 60)
    num_galleries = max(4, min(time_minutes // 5, 30))

    print(f"Time budget: {time_minutes} min → targeting {num_galleries} galleries\n")

    # Select target galleries
    target_galleries = select_galleries(merged, profile, num_galleries)
    print(f"Selected targets: {sorted(target_galleries)}\n")

    # Build route (physical path through connected rooms)
    route = build_walking_route(target_galleries, start=200)

    # Verify adjacency
    for i in range(len(route) - 1):
        a, b = route[i], route[i + 1]
        if b not in PHYSICAL_ADJACENCY.get(a, []):
            print(f"  WARNING: jump between {a} and {b}")

    print(f"Walking path: {' → '.join(str(g) for g in route)}\n")

    # Build output with artworks for each stop
    route_output = []
    total_time = 0
    seen_objects = set()  # Don't repeat artwork picks if we revisit a room
    visited_rooms = set()  # Track rooms already visited to handle backtracking

    for gnum in route:
        g_objs = merged[merged.gallery_number == gnum]
        is_target = gnum in target_galleries
        gal_info = graph["galleries"].get(str(gnum), {})
        is_revisit = gnum in visited_rooms
        visited_rooms.add(gnum)

        if is_revisit:
            # Walking back through — no time, no picks
            picks = []
            time_est = 1  # just passing through
        elif is_target and len(g_objs) > 0:
            picks = pick_artworks_for_gallery(g_objs, profile, max_picks=3)
            picks = [p for p in picks if p["object_id"] not in seen_objects]
            for p in picks:
                seen_objects.add(p["object_id"])
            time_est = 5
        elif len(g_objs) > 0:
            picks = pick_artworks_for_gallery(g_objs, profile, max_picks=1)
            picks = [p for p in picks if p["object_id"] not in seen_objects]
            for p in picks:
                seen_objects.add(p["object_id"])
            time_est = 2
        else:
            picks = []
            time_est = 3 if gnum == 217 else 1

        total_time += time_est

        stop = {
            "gallery": gnum,
            "name": gal_info.get("name", f"Gallery {gnum}"),
            "region": gal_info.get("region", ""),
            "is_target": is_target,
            "time_estimate_min": time_est,
            "object_count": len(g_objs),
            "featured_artworks": picks,
            "lat": gal_info.get("lat"),
            "lng": gal_info.get("lng"),
            "neighbors": gal_info.get("neighbors", []),
        }
        route_output.append(stop)

        marker = "★" if is_target else "→"
        art_str = f" | {picks[0]['title'][:40]}" if picks else ""
        print(f"  {marker} {gnum} {stop['name'][:35]:35s} ({len(g_objs):>3} obj, ~{time_est}m){art_str}")

    print(f"\n  Total: {total_time} min estimated")

    # Build path coordinates for map polyline
    path_coords = [
        {"gallery": s["gallery"], "lat": s["lat"], "lng": s["lng"]}
        for s in route_output if s["lat"] and s["lng"]
    ]

    lats = [s["lat"] for s in route_output if s["lat"]]
    lngs = [s["lng"] for s in route_output if s["lng"]]

    return {
        "profile_summary": {
            "time_budget": time_minutes,
            "num_target_galleries": len(target_galleries),
            "total_stops": len(route),
        },
        "route": route_output,
        "total_time_estimate": total_time,
        "path_coordinates": path_coords,
        "map_bounds": {
            "north": max(lats) + 0.0002,
            "south": min(lats) - 0.0002,
            "east": max(lngs) + 0.0002,
            "west": min(lngs) - 0.0002,
        } if lats else {},
    }


SAMPLE_PROFILES = {
    "ceramics_lover": {
        "time_budget_minutes": 60,
        "preferred_gallery": 200,
        "selected_object_ids": [42229, 39666],
        "weights": {
            "culture": {"east_asia": 0.8, "japan": 0.7, "korea": 0.5, "south_asia": 0.3, "southeast_asia": 0.3, "himalayan": 0.3},
            "classification": {"ceramics": 0.9, "jade": 0.5, "sculpture": 0.4, "metalwork": 0.3, "paintings": 0.3, "prints": 0.2, "furnishings": 0.2},
            "era": {"ancient": 0.4, "classical": 0.4, "medieval": 0.6, "early_modern": 0.8, "late_imperial": 0.9, "modern": 0.3},
        },
    },
    "sculpture_explorer": {
        "time_budget_minutes": 120,
        "preferred_gallery": 247,
        "selected_object_ids": [63532, 50799, 65095],
        "weights": {
            "culture": {"east_asia": 0.4, "japan": 0.3, "korea": 0.3, "south_asia": 0.8, "southeast_asia": 0.9, "himalayan": 0.7},
            "classification": {"sculpture": 0.9, "metalwork": 0.7, "ceramics": 0.3, "jade": 0.4, "paintings": 0.2, "prints": 0.1, "furnishings": 0.1},
            "era": {"ancient": 0.7, "classical": 0.8, "medieval": 0.9, "early_modern": 0.5, "late_imperial": 0.3, "modern": 0.2},
        },
    },
    "quick_highlights": {
        "time_budget_minutes": 30,
        "preferred_gallery": None,
        "selected_object_ids": [],
        "weights": {
            "culture": {"east_asia": 0.5, "japan": 0.5, "korea": 0.5, "south_asia": 0.5, "southeast_asia": 0.5, "himalayan": 0.5},
            "classification": {"ceramics": 0.5, "sculpture": 0.5, "metalwork": 0.5, "jade": 0.5, "paintings": 0.5, "prints": 0.5, "furnishings": 0.5},
            "era": {"ancient": 0.5, "classical": 0.5, "medieval": 0.5, "early_modern": 0.5, "late_imperial": 0.5, "modern": 0.5},
        },
    },
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="ceramics_lover", choices=SAMPLE_PROFILES.keys())
    parser.add_argument("--time", type=int, default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    profile = SAMPLE_PROFILES[args.profile]
    if args.time:
        profile["time_budget_minutes"] = args.time

    print(f"=== ROUTE: {args.profile} ===\n")
    result = generate_route(profile)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved to {args.output}")
