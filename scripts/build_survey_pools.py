#!/usr/bin/env python3
"""
Precompute image candidate pools for dynamic survey questions.
Output: data/survey_pools.json
"""

import pandas as pd
import json
import random

random.seed(42)

def main():
    meta = pd.read_csv("data/asian_art_on_view.csv")
    aug = pd.read_csv("data/augmented_fields.csv")
    desc = pd.read_csv("data/descriptions.csv")

    merged = meta.merge(aug, on="object_id", how="left")
    hf = desc[desc.is_primary == True][["object_id", "source_image_url", "output_alt_text"]]
    merged = merged.merge(hf, on="object_id", how="left")

    # Only objects with images
    merged = merged[merged.source_image_url.notna()].copy()

    # Add dimension tags
    culture_map = {
        "east_asia": ["China", "Chinese"],
        "japan": ["Japan"],
        "korea": ["Korea"],
        "south_asia": ["India", "Nepal", "Sri Lanka", "Bangladesh", "Pakistan"],
        "southeast_asia": ["Thailand", "Cambodia", "Indonesia", "Vietnam", "Burma"],
        "himalayan": ["Tibet"],
    }

    def get_culture_group(c):
        if pd.isna(c):
            return "other"
        for group, kws in culture_map.items():
            if any(kw.lower() in c.lower() for kw in kws):
                return group
        return "other"

    def get_era(d):
        if pd.isna(d):
            return "unknown"
        if d < -200: return "ancient"
        if d < 600: return "classical"
        if d < 1300: return "medieval"
        if d < 1600: return "early_modern"
        if d < 1900: return "late_imperial"
        return "modern"

    class_map = {
        "ceramics": ["Ceramics", "Tomb Pottery", "Glass"],
        "sculpture": ["Sculpture", "Ivories", "Horn", "Stone"],
        "metalwork": ["Metalwork", "Cloisonné", "Enamels", "Mirrors", "Jewelry"],
        "jade_hardstone": ["Jade", "Hardstone", "Snuff Bottles", "Bamboo"],
        "paintings": ["Paintings", "Calligraphy", "Manuscripts"],
        "prints": ["Prints", "Illustrated Books", "Rubbing"],
        "furnishings": ["Furniture", "Lacquer", "Wood", "Woodwork"],
    }

    def get_class_group(c):
        if pd.isna(c):
            return "other"
        for group, vals in class_map.items():
            if c in vals:
                return group
        return "other"

    merged["culture_group"] = merged.culture.apply(get_culture_group)
    merged["era"] = merged.object_begin_date.apply(get_era)
    merged["class_group"] = merged.classification.apply(get_class_group)

    # Build object cards (what the frontend needs to render a survey image)
    def make_card(row):
        img_url = row.source_image_url
        return {
            "id": int(row.object_id),
            "title": row.title,
            "culture": row.culture if pd.notna(row.culture) else "",
            "date": row.object_date if pd.notna(row.object_date) else "",
            "classification": row.classification if pd.notna(row.classification) else "",
            "gallery": int(row.gallery_number),
            "alt_text": row.output_alt_text if pd.notna(row.output_alt_text) else "",
            "image_url": img_url,
            "image_thumb": img_url.replace("/original/", "/mobile-large/"),
            "highlight": bool(row.is_highlight),
            "culture_group": row.culture_group,
            "era": row.era,
            "class_group": row.class_group,
        }

    # Prioritize highlights, then sort by gallery diversity
    highlights = merged[merged.is_highlight == True].copy()
    non_highlights = merged[merged.is_highlight == False].copy()

    # Build pools
    pools = {
        "by_classification": {},
        "by_culture": {},
        "by_era": {},
        "highlights": [],
        "all_cards": {},
    }

    # Highlights pool
    for _, row in highlights.iterrows():
        card = make_card(row)
        pools["highlights"].append(card)
        pools["all_cards"][card["id"]] = card

    # By classification
    for group in ["ceramics", "sculpture", "metalwork", "jade_hardstone", "paintings", "prints", "furnishings"]:
        subset = merged[merged.class_group == group]
        # Highlights first, then others
        hl = subset[subset.is_highlight == True]
        non_hl = subset[subset.is_highlight == False].sample(frac=1)
        ordered = pd.concat([hl, non_hl])
        cards = []
        for _, row in ordered.iterrows():
            card = make_card(row)
            cards.append(card)
            pools["all_cards"][card["id"]] = card
        pools["by_classification"][group] = cards

    # By culture
    for group in ["east_asia", "japan", "korea", "south_asia", "southeast_asia", "himalayan"]:
        subset = merged[merged.culture_group == group]
        hl = subset[subset.is_highlight == True]
        non_hl = subset[subset.is_highlight == False].sample(frac=1)
        ordered = pd.concat([hl, non_hl])
        cards = []
        seen_galleries = set()
        for _, row in ordered.iterrows():
            card = make_card(row)
            # Boost gallery diversity
            if card["gallery"] not in seen_galleries:
                cards.insert(0 if card["highlight"] else len([c for c in cards if c["highlight"]]), card)
            else:
                cards.append(card)
            seen_galleries.add(card["gallery"])
            pools["all_cards"][card["id"]] = card
        pools["by_culture"][group] = cards

    # By era
    for era in ["ancient", "classical", "medieval", "early_modern", "late_imperial", "modern"]:
        subset = merged[merged.era == era]
        hl = subset[subset.is_highlight == True]
        non_hl = subset[subset.is_highlight == False].sample(frac=1)
        ordered = pd.concat([hl, non_hl])
        pools["by_era"][era] = [make_card(row) for _, row in ordered.iterrows()]

    # Gallery preview images (best image per gallery for Q8)
    gallery_previews = {}
    with open("data/all_galleries.json") as f:
        all_gals = json.load(f)
    gal_names = {g["gallery_number"]: g.get("long_name", "") for g in all_gals if g.get("gallery_number")}

    for gnum in sorted(merged.gallery_number.unique()):
        g_data = merged[merged.gallery_number == gnum]
        # Pick best: highlight first, then random
        hl = g_data[g_data.is_highlight == True]
        if len(hl) > 0:
            best = hl.iloc[0]
        else:
            best = g_data.iloc[0]
        card = make_card(best)
        card["gallery_name"] = gal_names.get(str(int(gnum)), f"Gallery {int(gnum)}")
        card["gallery_object_count"] = len(g_data)
        gallery_previews[str(int(gnum))] = card

    pools["gallery_previews"] = gallery_previews

    # Q4/Q5 static material comparison pairs
    pools["material_pairs"] = {
        "q4": {
            "option_a": {"label": "ceramic", "class_group": "ceramics"},
            "option_b": {"label": "metal", "class_group": "metalwork"},
        },
        "q5": {
            "option_a": {"label": "stone", "class_group": "jade_hardstone"},
            "option_b": {"label": "wood", "class_group": "furnishings"},
        },
    }

    # Select representative images for Q4/Q5
    for q_key in ["q4", "q5"]:
        pair = pools["material_pairs"][q_key]
        for opt in ["option_a", "option_b"]:
            cg = pair[opt]["class_group"]
            candidates = pools["by_classification"].get(cg, [])
            # Pick the first highlight, or first item
            pick = candidates[0] if candidates else None
            pair[opt]["preview"] = pick

    # Emotion word grid
    pools["emotion_words"] = [
        "peaceful", "powerful", "playful", "mysterious",
        "ancient", "intricate", "spiritual", "surprising",
        "colorful", "monumental", "intimate", "earthy",
        "elegant", "fierce", "whimsical", "haunting",
    ]

    # Stats
    print(f"Built survey pools:")
    print(f"  Total object cards: {len(pools['all_cards'])}")
    print(f"  Highlights: {len(pools['highlights'])}")
    for group, cards in pools["by_classification"].items():
        print(f"  {group}: {len(cards)} objects ({sum(1 for c in cards if c['highlight'])} highlights)")
    print(f"  Gallery previews: {len(gallery_previews)}")

    # Don't save all_cards in the pool file (too big, and it's indexed)
    # Instead save just the IDs and the frontend can look up from gallery_objects.json
    output = {k: v for k, v in pools.items() if k != "all_cards"}

    # Trim pools to top 20 per category (enough for survey sampling)
    for key in ["by_classification", "by_culture", "by_era"]:
        for subkey in output[key]:
            output[key][subkey] = output[key][subkey][:20]
    output["highlights"] = output["highlights"][:30]

    with open("data/survey_pools.json", "w") as f:
        json.dump(output, f, indent=2)

    size = len(json.dumps(output))
    print(f"\n  Saved data/survey_pools.json ({size//1024}KB)")


if __name__ == "__main__":
    main()
