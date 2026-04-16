#!/usr/bin/env python3
"""
Generate a personalized route through the Asian Art wing.

Given a user profile (from survey), selects galleries and artworks,
then builds an ordered walking path.

Usage:
  python3 scripts/generate_route.py [--time 60] [--profile sample]
"""

import json
import math
import pandas as pd
from collections import defaultdict
import argparse

# --- Data loading ---

def load_data():
    meta = pd.read_csv("data/asian_art_on_view.csv")
    aug = pd.read_csv("data/augmented_fields.csv")
    desc = pd.read_csv("data/descriptions.csv")

    merged = meta.merge(aug, on="object_id", how="left")
    hf = desc[desc.is_primary == True][["object_id", "source_image_url", "output_alt_text"]]
    merged = merged.merge(hf, on="object_id", how="left")

    # Add dimension tags
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
    """Score a single artwork against a user profile. Returns 0-1."""
    weights = profile["weights"]
    score = 0.0

    # Culture match
    cg = obj["culture_group"]
    score += weights.get("culture", {}).get(cg, 0.3) * 0.3

    # Classification match
    cl = obj["class_group"]
    score += weights.get("classification", {}).get(cl, 0.3) * 0.3

    # Era match
    era = obj["era"]
    score += weights.get("era", {}).get(era, 0.3) * 0.2

    # Highlight bonus
    if obj.get("is_highlight"):
        score += 0.1

    # Selected object bonus (if user picked this in survey)
    if obj.get("object_id") in profile.get("selected_object_ids", []):
        score += 0.3

    return min(score, 1.0)


def score_gallery(gallery_objects, profile):
    """Score a gallery based on its objects and the user profile."""
    if len(gallery_objects) == 0:
        return 0.0

    scores = [score_object(obj, profile) for _, obj in gallery_objects.iterrows()]
    # Gallery score: mean of top 5 objects (not all — we highlight the best)
    top_scores = sorted(scores, reverse=True)[:5]
    return sum(top_scores) / len(top_scores)


# --- Route building ---

def find_path_bfs(graph, start, end):
    """BFS shortest path using the gallery graph."""
    galleries = graph["galleries"]
    if str(start) not in galleries or str(end) not in galleries:
        return None

    visited = {start}
    queue = [[start]]

    while queue:
        path = queue.pop(0)
        current = path[-1]
        gal = galleries.get(str(current), {})

        for neighbor in gal.get("neighbors", []):
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return None


def build_walking_route(graph, target_galleries, start=200):
    """Nearest-neighbor walk through target galleries."""
    remaining = set(target_galleries)
    route = []
    current = start

    if current in remaining:
        remaining.remove(current)
    route.append(current)

    while remaining:
        best = None
        best_path = None
        best_len = float("inf")

        for target in remaining:
            path = find_path_bfs(graph, current, target)
            if path and len(path) < best_len:
                best_len = len(path)
                best = target
                best_path = path

        if best is None:
            # Can't reach remaining galleries, just append them
            route.extend(sorted(remaining))
            break

        for g in best_path[1:]:
            if g not in route:
                route.append(g)

        remaining.remove(best)
        current = best

    return route


def select_galleries(merged, graph, profile, num_galleries):
    """
    Select galleries to visit based on profile, with diversity constraints.
    """
    gallery_scores = {}
    gallery_data = {}

    for gnum in merged.gallery_number.unique():
        if gnum > 253:  # Skip non-Asian-Art galleries
            continue
        g_objs = merged[merged.gallery_number == gnum]
        gallery_data[int(gnum)] = g_objs
        gallery_scores[int(gnum)] = score_gallery(g_objs, profile)

    # Greedy selection with diversity penalty
    selected = []
    used_cultures = defaultdict(int)
    used_classes = defaultdict(int)

    # Always include Chinese Garden (217) and preferred gallery
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

            # Diversity penalty
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
    """Pick 2-3 featured artworks per gallery."""
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
            "title": obj.title,
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

    # Calculate number of galleries from time budget
    time_minutes = profile.get("time_budget_minutes", 60)
    num_galleries = max(4, min(time_minutes // 5, 30))

    print(f"Time budget: {time_minutes} min → {num_galleries} galleries\n")

    # Select galleries
    target_galleries = select_galleries(merged, graph, profile, num_galleries)
    print(f"Selected {len(target_galleries)} target galleries: {sorted(target_galleries)}\n")

    # Build walking route
    route = build_walking_route(graph, target_galleries, start=200)
    print(f"Walking route ({len(route)} total stops):\n")

    # Pick artworks for each gallery on route
    route_output = []
    total_time = 0

    for gnum in route:
        g_objs = merged[merged.gallery_number == gnum]
        is_target = gnum in target_galleries
        gal_info = graph["galleries"].get(str(gnum), {})

        # Pick artworks (more for target galleries, 1 for pass-through)
        if is_target and len(g_objs) > 0:
            picks = pick_artworks_for_gallery(g_objs, profile, max_picks=3)
            time_est = 5
        elif len(g_objs) > 0:
            picks = pick_artworks_for_gallery(g_objs, profile, max_picks=1)
            time_est = 2
        else:
            picks = []
            time_est = 2 if gnum == 217 else 1  # Garden gets extra time

        total_time += time_est

        stop = {
            "gallery": gnum,
            "name": gal_info.get("name", f"Gallery {gnum}"),
            "region": gal_info.get("region", ""),
            "is_target": is_target,
            "time_estimate_min": time_est,
            "object_count": len(g_objs),
            "featured_artworks": picks,
        }
        route_output.append(stop)

        # Print
        marker = "★" if is_target else "→"
        print(f"  {marker} Gallery {gnum}: {stop['name']} ({len(g_objs)} objects, ~{time_est} min)")
        for p in picks:
            tag_icon = {"affinity": "♥", "stretch": "◆", "wildcard": "✦"}.get(p["tag"], "·")
            print(f"      {tag_icon} {p['title']} ({p['culture']}, {p['date']}) [{p['score']}]")

    print(f"\n  Total estimated time: {total_time} minutes")

    result = {
        "profile_summary": {
            "time_budget": time_minutes,
            "num_target_galleries": len(target_galleries),
            "total_stops": len(route),
        },
        "route": route_output,
        "total_time_estimate": total_time,
    }

    return result


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
