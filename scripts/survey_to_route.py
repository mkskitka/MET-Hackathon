#!/usr/bin/env python3
"""
Convert survey output JSON into a personalized route with reasons.

Takes the survey answers (q1-q9) and produces a route where:
- Every room on the path has at least 1 highlighted artwork
- Each artwork has a reason tied back to survey answers
- The route itself has a narrative explanation

Usage:
  python3 scripts/survey_to_route.py --input survey.json --output route.json
  python3 scripts/survey_to_route.py --example
"""

import json
import argparse
import sys
sys.path.insert(0, "scripts")
from generate_route import (
    load_data, build_walking_route, order_targets_optimal,
    score_object, pick_artworks_for_gallery,
    PHYSICAL_ADJACENCY, find_shortest_path,
    get_culture_group, get_era, get_class_group
)
import pandas as pd
from collections import defaultdict


# --- Survey answer → profile conversion ---

MATERIAL_TO_CLASS = {
    "ceramic": "ceramics", "ceramics": "ceramics",
    "metal": "metalwork", "metalwork": "metalwork",
    "stone": "jade", "jade_hardstone": "jade",
    "wood": "furnishings", "furnishings": "furnishings",
    "sculpture": "sculpture",
    "paintings": "paintings",
    "prints": "prints",
}

CULTURE_LABELS = {
    "east_asia": "Chinese",
    "japan": "Japanese",
    "korea": "Korean",
    "south_asia": "South Asian",
    "southeast_asia": "Southeast Asian",
    "himalayan": "Himalayan",
}

DEPTH_LABELS = {
    "focused": "deep-dive",
    "mixed": "mixed",
    "variety": "variety-packed",
}

FREEDOM_LABELS = {
    "curated": "guided",
    "balanced": "balanced",
    "free": "free-spirited",
}


def survey_to_profile(answers):
    """Convert raw survey answers to a weighted profile."""
    time_budget = int(answers.get("q1", 60))
    freedom = answers.get("q2", "balanced")
    depth = answers.get("q3", "mixed")
    materials = answers.get("q4", [])
    regions = answers.get("q5", [])
    q6_pick = answers.get("q6", "")
    q7_picks = answers.get("q7", [])
    preferred_gallery = answers.get("q8", "")
    emotions = answers.get("q9", [])

    if isinstance(materials, str):
        materials = [materials]
    if isinstance(regions, str):
        regions = [regions]
    if isinstance(q7_picks, str):
        q7_picks = [q7_picks]
    if isinstance(emotions, str):
        emotions = [emotions]

    # Build classification weights
    class_weights = {
        "ceramics": 0.3, "sculpture": 0.3, "metalwork": 0.3,
        "jade": 0.3, "paintings": 0.3, "prints": 0.2, "furnishings": 0.2,
    }
    for m in materials:
        key = MATERIAL_TO_CLASS.get(m, m)
        if key in class_weights:
            class_weights[key] = min(class_weights[key] + 0.4, 0.9)

    # Build culture weights
    culture_weights = {
        "east_asia": 0.3, "japan": 0.3, "korea": 0.3,
        "south_asia": 0.3, "southeast_asia": 0.3, "himalayan": 0.3,
    }
    for r in regions:
        if r in culture_weights:
            culture_weights[r] = min(culture_weights[r] + 0.4, 0.9)

    # Era weights (from emotions / depth)
    era_weights = {
        "ancient": 0.4, "classical": 0.4, "medieval": 0.5,
        "early_modern": 0.5, "late_imperial": 0.5, "modern": 0.3,
    }
    emotion_lower = [e.lower() for e in emotions]
    if any(w in emotion_lower for w in ["ancient", "earthy", "powerful"]):
        era_weights["ancient"] += 0.3
        era_weights["classical"] += 0.2
    if any(w in emotion_lower for w in ["intricate", "elegant", "colorful"]):
        era_weights["late_imperial"] += 0.3
        era_weights["early_modern"] += 0.2
    if any(w in emotion_lower for w in ["spiritual", "peaceful", "haunting"]):
        era_weights["medieval"] += 0.2

    # Selected object IDs
    selected_ids = []
    if q6_pick:
        try:
            selected_ids.append(int(q6_pick))
        except ValueError:
            pass
    for pick in q7_picks:
        try:
            selected_ids.append(int(pick))
        except ValueError:
            pass

    # Preferred gallery
    pref_gallery = None
    if preferred_gallery:
        try:
            pref_gallery = int(preferred_gallery.replace("Gallery ", ""))
        except ValueError:
            pass

    profile = {
        "time_budget_minutes": time_budget,
        "preferred_gallery": pref_gallery,
        "selected_object_ids": selected_ids,
        "weights": {
            "culture": culture_weights,
            "classification": class_weights,
            "era": era_weights,
        },
        # Keep raw answers for reason generation
        "_raw": {
            "freedom": freedom,
            "depth": depth,
            "materials": materials,
            "regions": regions,
            "emotions": emotions,
            "q6_pick": q6_pick,
            "q7_picks": q7_picks,
            "preferred_gallery": preferred_gallery,
        }
    }
    return profile


# --- Reason generation ---

def generate_artwork_reason(obj, profile, tag):
    """Generate a human-readable reason why this artwork was picked."""
    raw = profile.get("_raw", {})
    materials = raw.get("materials", [])
    regions = raw.get("regions", [])
    emotions = raw.get("emotions", [])
    selected_ids = profile.get("selected_object_ids", [])

    title = obj.get("title", "").strip()
    culture = obj.get("culture", "")
    classification = obj.get("classification", "")
    date = obj.get("date", "")
    alt_text = obj.get("alt_text", "")

    # Direct selection from survey
    oid = obj.get("object_id")
    if oid in selected_ids:
        return f"You picked this in the survey — come see it in person."

    # Classification match
    obj_class = get_class_group(classification)
    matched_materials = [m for m in materials if MATERIAL_TO_CLASS.get(m, m) == obj_class]

    # Culture match
    obj_culture = get_culture_group(culture)
    matched_regions = [r for r in regions if r == obj_culture]

    if tag == "affinity":
        parts = []
        if matched_materials:
            parts.append(f"you said you love {matched_materials[0]}")
        if matched_regions:
            label = CULTURE_LABELS.get(matched_regions[0], matched_regions[0])
            parts.append(f"you're drawn to {label} art")
        if obj.get("highlight"):
            parts.append("it's a museum highlight")
        if parts:
            return f"Picked because {' and '.join(parts)}."
        return f"Highly matched to your interests."

    elif tag == "stretch":
        if matched_materials and not matched_regions:
            label = CULTURE_LABELS.get(obj_culture, culture)
            return f"Same {matched_materials[0]} you love, but from {label} — a fresh perspective."
        elif matched_regions and not matched_materials:
            return f"From the {CULTURE_LABELS.get(obj_culture, '')} tradition you're interested in, but in a different medium — {classification.lower()}."
        else:
            return f"Something a little different — see how {classification.lower()} from {culture} adds to your journey."

    else:  # wildcard
        if obj.get("highlight"):
            return f"A museum highlight you'll pass right by — worth a look."
        emotion_match = [e for e in emotions if e.lower() in (alt_text or "").lower()]
        if emotion_match:
            return f"This has the '{emotion_match[0].lower()}' energy you're after."
        return f"A hidden gem — let yourself be surprised."


def generate_room_reason(gallery_num, gallery_info, profile, is_target):
    """Generate a reason why this room is on the path."""
    raw = profile.get("_raw", {})
    materials = raw.get("materials", [])
    regions = raw.get("regions", [])
    pref = raw.get("preferred_gallery", "")

    name = gallery_info.get("name", f"Gallery {gallery_num}")

    if str(gallery_num) == str(pref):
        return f"You chose this gallery in the survey — this is your pick."

    if gallery_num == 217:
        return "The Chinese Garden — a peaceful oasis everyone should experience."

    if not is_target:
        return f"You'll pass through here on your way — keep an eye out."

    # Check what's in the room vs what user wants
    top_class = gallery_info.get("top_classifications", {})
    region = gallery_info.get("region", "")

    for m in materials:
        key = MATERIAL_TO_CLASS.get(m, m)
        for cls_name in top_class:
            if get_class_group(cls_name) == key:
                return f"This gallery is rich in {m} — right up your alley."

    region_labels = {
        "japanese": "Japanese", "south_asian": "South Asian",
        "southeast_asian": "Southeast Asian", "himalayan": "Himalayan",
        "chinese_ceramics": "Chinese ceramic", "chinese_ancient": "ancient Chinese",
        "chinese_painting": "Chinese painting", "korean": "Korean",
    }
    for r in regions:
        if r in (region or ""):
            label = CULTURE_LABELS.get(r, r)
            return f"You wanted to see {label} art — this gallery delivers."

    return f"A great stop that complements your interests."


def generate_route_summary(profile, route_data):
    """Generate an overall summary of why this route was created."""
    raw = profile.get("_raw", {})
    time = profile["time_budget_minutes"]
    freedom = FREEDOM_LABELS.get(raw.get("freedom", ""), "")
    depth = DEPTH_LABELS.get(raw.get("depth", ""), "")
    materials = raw.get("materials", [])
    regions = raw.get("regions", [])
    emotions = raw.get("emotions", [])

    mat_str = " and ".join(materials[:3]) if materials else "various art forms"
    region_str = ", ".join(CULTURE_LABELS.get(r, r) for r in regions[:3]) if regions else "diverse cultures"
    emotion_str = ", ".join(e.lower() for e in emotions[:3]) if emotions else ""

    target_count = sum(1 for s in route_data["route"] if s["is_target"])
    total_stops = len(route_data["route"])

    summary = f"Your {time}-minute {depth} tour"
    if freedom:
        summary += f" ({freedom} style)"
    summary += f" visits {target_count} key galleries across {total_stops} rooms."
    summary += f" We focused on {mat_str} from {region_str}."
    if emotion_str:
        summary += f" You're looking for something {emotion_str} — we kept that in mind."

    return summary


# --- Main route generation with reasons ---

def generate_route_with_reasons(survey_answers):
    """Full pipeline: survey answers → profile → route → reasons."""
    profile = survey_to_profile(survey_answers)
    merged, graph = load_data()

    time_minutes = profile["time_budget_minutes"]
    num_galleries = max(4, min(time_minutes // 5, 30))

    # Select target galleries
    gallery_scores = {}
    gallery_data = {}
    for gnum in merged.gallery_number.unique():
        if gnum > 253:
            continue
        g_objs = merged[merged.gallery_number == gnum]
        gallery_data[int(gnum)] = g_objs
        scores = []
        for _, obj in g_objs.iterrows():
            scores.append(score_object(obj, profile))
        top = sorted(scores, reverse=True)[:5]
        gallery_scores[int(gnum)] = sum(top) / len(top) if top else 0

    # Greedy selection with diversity
    selected = []
    used_cultures = defaultdict(int)
    used_classes = defaultdict(int)

    must_visit = [217]
    if profile.get("preferred_gallery") and profile["preferred_gallery"] in gallery_scores:
        must_visit.append(profile["preferred_gallery"])

    for g in must_visit:
        if g in gallery_scores:
            selected.append(g)

    while len(selected) < num_galleries:
        best_g = None
        best_s = -1
        for gnum, base in gallery_scores.items():
            if gnum in selected or not gallery_data.get(gnum) is not None or len(gallery_data.get(gnum, [])) == 0:
                continue
            g_objs = gallery_data[gnum]
            top_culture = g_objs.culture_group.mode() if hasattr(g_objs, 'culture_group') else pd.Series()
            top_class = g_objs.class_group.mode() if hasattr(g_objs, 'class_group') else pd.Series()
            penalty = 0
            if len(top_culture) > 0 and used_cultures[top_culture.iloc[0]] >= 2:
                penalty += 0.15 * used_cultures[top_culture.iloc[0]]
            if len(top_class) > 0 and used_classes[top_class.iloc[0]] >= 2:
                penalty += 0.1 * used_classes[top_class.iloc[0]]
            adj = base - penalty
            if adj > best_s:
                best_s = adj
                best_g = gnum
        if best_g is None:
            break
        selected.append(best_g)
        g_objs = gallery_data[best_g]
        if hasattr(g_objs, 'culture_group'):
            tc = g_objs.culture_group.mode()
            if len(tc) > 0:
                used_cultures[tc.iloc[0]] += 1
        if hasattr(g_objs, 'class_group'):
            tc = g_objs.class_group.mode()
            if len(tc) > 0:
                used_classes[tc.iloc[0]] += 1

    # Build walking route
    route = build_walking_route(selected, start=200)

    # Build output with reasons
    route_output = []
    total_time = 0
    seen_objects = set()
    visited_rooms = set()

    for gnum in route:
        g_objs = merged[merged.gallery_number == gnum]
        is_target = gnum in selected
        gal_info = graph["galleries"].get(str(gnum), {})
        is_revisit = gnum in visited_rooms
        visited_rooms.add(gnum)

        if is_revisit:
            picks = []
            time_est = 1
        elif is_target and len(g_objs) > 0:
            picks = pick_artworks_for_gallery(g_objs, profile, max_picks=3)
            picks = [p for p in picks if p["object_id"] not in seen_objects]
            time_est = 5
        elif len(g_objs) > 0:
            picks = pick_artworks_for_gallery(g_objs, profile, max_picks=1)
            picks = [p for p in picks if p["object_id"] not in seen_objects]
            time_est = 2
        else:
            picks = []
            time_est = 3 if gnum == 217 else 1

        for p in picks:
            seen_objects.add(p["object_id"])

        # Add reasons to each artwork
        for p in picks:
            p["reason"] = generate_artwork_reason(p, profile, p["tag"])

        # Room reason
        room_reason = generate_room_reason(gnum, gal_info, profile, is_target)

        total_time += time_est

        stop = {
            "gallery": gnum,
            "name": gal_info.get("name", f"Gallery {gnum}"),
            "region": gal_info.get("region", ""),
            "is_target": is_target,
            "is_revisit": is_revisit,
            "time_estimate_min": time_est,
            "object_count": len(g_objs),
            "reason": room_reason,
            "featured_artworks": picks,
            "lat": gal_info.get("lat"),
            "lng": gal_info.get("lng"),
            "neighbors": gal_info.get("neighbors", []),
        }
        route_output.append(stop)

    # Path coordinates for map
    path_coords = [
        {"gallery": s["gallery"], "lat": s["lat"], "lng": s["lng"]}
        for s in route_output if s["lat"] and s["lng"]
    ]
    lats = [s["lat"] for s in route_output if s["lat"]]
    lngs = [s["lng"] for s in route_output if s["lng"]]

    result = {
        "profile_summary": {
            "time_budget": time_minutes,
            "num_target_galleries": len(selected),
            "total_stops": len(route),
            "freedom": profile["_raw"]["freedom"],
            "depth": profile["_raw"]["depth"],
            "materials": profile["_raw"]["materials"],
            "regions": profile["_raw"]["regions"],
            "emotions": profile["_raw"]["emotions"],
        },
        "route_summary": "",
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

    result["route_summary"] = generate_route_summary(profile, result)

    return result


# Example survey answers matching the survey_test.html output format
EXAMPLE_SURVEYS = {
    "ceramic_spiritual": {
        "q1": 60,
        "q2": "balanced",
        "q3": "focused",
        "q4": ["ceramics", "jade_hardstone"],
        "q5": ["east_asia", "japan"],
        "q6": "39666",
        "q7": ["42229", "39844"],
        "q8": "207",
        "q9": ["Ancient", "Intricate", "Peaceful", "Elegant", "Spiritual"]
    },
    "quick_adventure": {
        "q1": 30,
        "q2": "free",
        "q3": "variety",
        "q4": ["sculpture"],
        "q5": ["southeast_asia", "himalayan"],
        "q6": "63532",
        "q7": ["50799", "65095"],
        "q8": "247",
        "q9": ["Powerful", "Mysterious", "Surprising", "Fierce", "Ancient"]
    },
    "decorative_explorer": {
        "q1": 120,
        "q2": "curated",
        "q3": "mixed",
        "q4": ["metalwork", "ceramics", "furnishings"],
        "q5": ["east_asia", "korea", "japan"],
        "q6": "42183",
        "q7": ["39496", "47258"],
        "q8": "219",
        "q9": ["Elegant", "Colorful", "Intricate", "Playful", "Intimate"]
    },
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Survey JSON file")
    parser.add_argument("--output", help="Output route JSON file")
    parser.add_argument("--example", action="store_true", help="Run all examples")
    args = parser.parse_args()

    if args.example:
        for name, answers in EXAMPLE_SURVEYS.items():
            print(f"\n{'='*60}")
            print(f"=== {name} ===")
            print(f"{'='*60}\n")
            result = generate_route_with_reasons(answers)

            print(f"Summary: {result['route_summary']}\n")

            for stop in result["route"]:
                marker = "★" if stop["is_target"] else ("↩" if stop.get("is_revisit") else "→")
                print(f"  {marker} Gallery {stop['gallery']} — {stop['name'][:40]}")
                print(f"    Why: {stop['reason']}")
                for art in stop["featured_artworks"]:
                    tag_icon = {"affinity": "♥", "stretch": "◆", "wildcard": "✦"}.get(art["tag"], "·")
                    print(f"      {tag_icon} {art['title'][:50]}")
                    print(f"        → {art['reason']}")
                print()

            with open(f"data/sample_route_{name}.json", "w") as f:
                json.dump(result, f, indent=2)
            print(f"  Saved data/sample_route_{name}.json")

    elif args.input:
        with open(args.input) as f:
            answers = json.load(f)
        result = generate_route_with_reasons(answers)
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Saved to {args.output}")
        else:
            print(json.dumps(result, indent=2))
    else:
        parser.print_help()
