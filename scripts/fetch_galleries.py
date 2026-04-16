#!/usr/bin/env python3
"""
Fetch all gallery features from the Living Map API for The Met.
Outputs a JSON file with gallery number, name, center coordinates, floor, and description.
"""

import json
import urllib.request
import urllib.parse
import time
import sys

BASE = "https://map-api.prod.livingmap.com/v1/maps/the_met"
MET_CENTER = (40.779448, -73.963517)

def fetch_json(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def search_galleries(query, floor_id=None, limit=50):
    params = {
        "query": query,
        "latitude": MET_CENTER[0],
        "longitude": MET_CENTER[1],
        "limit": limit,
        "lang": "en-GB",
    }
    if floor_id:
        params["floor_id"] = floor_id
    url = f"{BASE}/search?{urllib.parse.urlencode(params)}"
    return fetch_json(url)

def fetch_feature_names():
    url = f"{BASE}/feature-names?lang=en-GB"
    return fetch_json(url)

def fetch_feature_by_name(name):
    url = f"{BASE}/features/?long_name={urllib.parse.quote(name)}&lang=en-GB"
    try:
        return fetch_json(url)
    except Exception as e:
        return None

def main():
    print("=== Fetching feature names ===")
    names_data = fetch_feature_names()

    # Save raw feature names
    with open("data/feature_names.json", "w") as f:
        json.dump(names_data, f, indent=2)
    print(f"Saved feature names to data/feature_names.json")

    # Now search for galleries across all floors
    all_galleries = {}
    floor_ids = {
        1: "Floor G",
        2: "Floor 1",
        3: "Floor 1M",
        4: "Floor 2",
        5: "Floor 3",
    }

    # Search with different queries to maximize coverage
    queries = [
        "gallery",
        "room",
        "wing",
        "collection",
        "art",
        "paintings",
        "sculpture",
        "armor",
        "egyptian",
        "greek",
        "roman",
        "asian",
        "chinese",
        "japanese",
        "islamic",
        "medieval",
        "american",
        "european",
        "modern",
        "instruments",
        "costume",
        "photographs",
        "temple",
        "period room",
        "arms",
        "african",
        "oceania",
    ]

    for query in queries:
        for floor_id in floor_ids:
            try:
                result = search_galleries(query, floor_id=floor_id, limit=50)
                for item in result.get("data", []):
                    fid = item["id"]
                    if fid not in all_galleries:
                        gallery_num = item["label"]["name"][0]["text"] if item["label"]["name"] else None
                        long_name = None
                        if item["information"]["long_name"]:
                            long_name = item["information"]["long_name"][0]["text"]
                        summary = None
                        if item["information"]["summary"]:
                            summary = item["information"]["summary"][0]["text"]
                        description = None
                        if item["information"]["description"]:
                            description = item["information"]["description"][0]["text"]

                        all_galleries[fid] = {
                            "id": fid,
                            "uid": item["uid"],
                            "gallery_number": gallery_num,
                            "long_name": long_name,
                            "summary": summary,
                            "category": item["categories"]["category"]["id"],
                            "subcategory": item["categories"]["subcategory"]["id"],
                            "is_temporarily_closed": item["is_temporarily_closed"],
                            "center_lat": item["location"]["center"]["latitude"],
                            "center_lng": item["location"]["center"]["longitude"],
                            "floor_id": item["location"]["floor"]["id"],
                            "floor_name": item["location"]["floor"]["name"][0]["text"],
                            "floor_short": item["location"]["floor"]["short_name"],
                            "description": description,
                            "image_url": item["media"]["popup"]["url"] if item["media"]["popup"] else None,
                        }
                time.sleep(0.1)  # Be polite
            except Exception as e:
                print(f"  Error searching '{query}' floor {floor_id}: {e}", file=sys.stderr)

    # Sort by gallery number
    galleries_list = sorted(all_galleries.values(), key=lambda g: g.get("gallery_number", ""))

    print(f"\n=== Found {len(galleries_list)} unique features ===")

    # Count by type
    by_subcat = {}
    for g in galleries_list:
        sc = g["subcategory"]
        by_subcat[sc] = by_subcat.get(sc, 0) + 1
    for sc, count in sorted(by_subcat.items(), key=lambda x: -x[1]):
        print(f"  {sc}: {count}")

    # Count galleries by floor
    by_floor = {}
    for g in galleries_list:
        fl = g["floor_name"]
        by_floor[fl] = by_floor.get(fl, 0) + 1
    print("\nBy floor:")
    for fl, count in sorted(by_floor.items()):
        print(f"  {fl}: {count}")

    # Save all galleries
    with open("data/all_galleries.json", "w") as f:
        json.dump(galleries_list, f, indent=2)
    print(f"\nSaved all gallery data to data/all_galleries.json")

    # Also save a simplified version - just gallery number, name, floor, coordinates
    simplified = []
    for g in galleries_list:
        if g["subcategory"] == "gallery":
            simplified.append({
                "gallery_number": g["gallery_number"],
                "name": g["long_name"],
                "floor": g["floor_short"],
                "lat": g["center_lat"],
                "lng": g["center_lng"],
                "closed": g["is_temporarily_closed"],
            })

    with open("data/gallery_points.json", "w") as f:
        json.dump(simplified, f, indent=2)
    print(f"Saved {len(simplified)} gallery point locations to data/gallery_points.json")

if __name__ == "__main__":
    main()
